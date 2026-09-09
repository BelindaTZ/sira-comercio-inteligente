"""VentasRepository (T023) — acceso a datos de `ventas` / `venta_detalle` y los
efectos de una venta sobre el inventario (lotes, movimientos). Sin lógica de
negocio (Principio XI): sólo consultas y escrituras.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.intento_pago_tarjeta import IntentoPagoTarjeta
from src.models.inventario import Inventario
from src.models.lote import Lote
from src.models.medio_pago import MedioPago
from src.models.movimiento_inventario import MovimientoInventario
from src.models.producto import Producto
from src.models.venta import Venta
from src.models.venta_detalle import VentaDetalle
from src.shared.repository import BaseRepository


class VentasRepository(BaseRepository[Venta]):
    model = Venta

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # --- ventas ---
    async def get_venta(self, venta_id: int) -> Venta | None:
        return await self.session.get(Venta, venta_id)

    async def lineas_de(self, venta_id: int) -> list[VentaDetalle]:
        stmt = (
            select(VentaDetalle)
            .where(VentaDetalle.venta_id == venta_id)
            .order_by(VentaDetalle.venta_detalle_id)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_linea(self, venta_id: int, linea_id: int) -> VentaDetalle | None:
        stmt = select(VentaDetalle).where(
            VentaDetalle.venta_detalle_id == linea_id,
            VentaDetalle.venta_id == venta_id,
        )
        return (await self.session.scalars(stmt)).first()

    async def total_de(self, venta_id: int) -> Decimal:
        stmt = select(
            func.coalesce(func.sum(VentaDetalle.cantidad * VentaDetalle.sales_value), 0)
        ).where(VentaDetalle.venta_id == venta_id)
        return Decimal(str(await self.session.scalar(stmt) or 0))

    # --- productos ---
    async def get_producto(self, product_id: int) -> Producto | None:
        return await self.session.get(Producto, product_id)

    async def get_producto_por_barcode(self, codigo_barras: str) -> Producto | None:
        stmt = select(Producto).where(Producto.codigo_barras == codigo_barras)
        return (await self.session.scalars(stmt)).first()

    async def catalogo_pos(
        self,
        *,
        tienda_id: int,
        search: str | None,
        categoria: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        """Productos con precio y stock en una tienda, para el grid del POS
        (registro rápido). Sólo `activo` y con `precio_base`."""
        cond = [
            "p.activo",
            "p.precio_base IS NOT NULL",
            "p.precio_base > 0",
            "i.cantidad_disponible > 0",
        ]
        binds: dict = {"t": tienda_id, "offset": offset, "limit": limit}
        if search and search.strip():
            s = search.strip()
            if s.isdigit():
                cond.append("(p.product_id = :sid OR p.codigo_barras = :sbar)")
                binds["sid"] = int(s)
                binds["sbar"] = s
            else:
                cond.append("(p.nombre ILIKE :q OR p.marca ILIKE :q OR p.product_type ILIKE :q)")
                binds["q"] = f"%{s}%"
        if categoria:
            cond.append("p.product_category = :cat")
            binds["cat"] = categoria
        where = " AND ".join(cond)
        base = (
            "FROM productos p JOIN inventario i "
            "ON i.product_id = p.product_id AND i.tienda_id = :t "
            f"WHERE {where}"
        )
        total = await self.session.scalar(text(f"SELECT count(*) {base}"), binds) or 0
        rows = await self.session.execute(
            text(f"""
            SELECT p.product_id, p.nombre, p.marca, p.product_category,
                   p.codigo_barras, p.imagen_url, p.precio_base,
                   i.cantidad_disponible AS stock_disponible
            {base}
            ORDER BY p.clasificacion_abc NULLS LAST, p.nombre
            OFFSET :offset LIMIT :limit
            """),
            binds,
        )
        return [dict(r._mapping) for r in rows], int(total)

    async def categorias_con_stock(self, tienda_id: int, limite: int = 10) -> list[str]:
        """Las categorías con más productos disponibles — para las pills del POS."""
        rows = await self.session.execute(
            text("""
            SELECT p.product_category, count(*) AS n
            FROM productos p JOIN inventario i
              ON i.product_id = p.product_id AND i.tienda_id = :t
            WHERE p.activo AND p.precio_base > 0 AND i.cantidad_disponible > 0
              AND p.product_category IS NOT NULL
            GROUP BY p.product_category
            ORDER BY n DESC, p.product_category
            LIMIT :lim
            """),
            {"t": tienda_id, "lim": limite},
        )
        return [r.product_category for r in rows]

    # --- inventario / lotes ---
    async def stock_disponible(self, product_id: int, tienda_id: int) -> int:
        stmt = select(Inventario.cantidad_disponible).where(
            Inventario.product_id == product_id, Inventario.tienda_id == tienda_id
        )
        return int(await self.session.scalar(stmt) or 0)

    async def lotes_para_consumo(self, product_id: int, tienda_id: int) -> list[Lote]:
        """Lotes con saldo, en orden FIFO/FEFO determinístico y bloqueados
        (`FOR UPDATE`) para evitar sobreventa concurrente (research.md #4, FR-006)."""
        stmt = (
            select(Lote)
            .where(
                Lote.product_id == product_id,
                Lote.tienda_id == tienda_id,
                Lote.cantidad_disponible > 0,
            )
            .order_by(
                Lote.fecha_vencimiento.asc().nulls_last(),
                Lote.cantidad_recibida.asc(),
                Lote.lote_id.asc(),
            )
            .with_for_update()
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_inventario_for_update(self, product_id: int, tienda_id: int) -> Inventario | None:
        stmt = (
            select(Inventario)
            .where(
                Inventario.product_id == product_id,
                Inventario.tienda_id == tienda_id,
            )
            .with_for_update()
        )
        return (await self.session.scalars(stmt)).first()

    async def get_lote_for_update(self, lote_id: int) -> Lote | None:
        stmt = select(Lote).where(Lote.lote_id == lote_id).with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def movimientos_salida_de(self, venta_id: int) -> list[MovimientoInventario]:
        """Movimientos de salida generados al confirmar esta venta (para revertir)."""
        linea_ids = select(VentaDetalle.venta_detalle_id).where(VentaDetalle.venta_id == venta_id)
        stmt = select(MovimientoInventario).where(
            MovimientoInventario.tipo == "salida",
            MovimientoInventario.referencia_tabla == "venta_detalle",
            MovimientoInventario.referencia_id.in_(linea_ids),
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_medio_pago(self, medio_pago_id: int) -> MedioPago | None:
        return await self.session.get(MedioPago, medio_pago_id)

    # --- feature 007: medios de pago (alta/baja/disponibles) ---
    async def get_medio_pago_por_nombre(self, nombre: str) -> MedioPago | None:
        stmt = select(MedioPago).where(func.lower(MedioPago.nombre) == nombre.lower())
        return (await self.session.scalars(stmt)).first()

    async def listar_medios_pago(self, aprobado: bool | None = None) -> list[MedioPago]:
        stmt = select(MedioPago)
        if aprobado is not None:
            stmt = stmt.where(MedioPago.aprobado.is_(aprobado))
        return list((await self.session.scalars(stmt.order_by(MedioPago.medio_pago_id))).all())

    async def medios_pago_disponibles(self) -> list[MedioPago]:
        stmt = (
            select(MedioPago)
            .where(MedioPago.aprobado.is_(True), MedioPago.fecha_baja.is_(None))
            .order_by(MedioPago.medio_pago_id)
        )
        return list((await self.session.scalars(stmt)).all())

    async def crear_medio_pago(self, medio: MedioPago) -> MedioPago:
        self.session.add(medio)
        await self.session.flush()
        await self.session.refresh(medio)
        return medio

    # --- feature 007: estado del datáfono de una caja (consulta cruzada a modules/caja) ---
    async def datafonos_de_caja(self, caja_id: int) -> list[str]:
        rows = await self.session.execute(
            text("SELECT estado FROM datafonos WHERE caja_id = :c ORDER BY datafono_id"),
            {"c": caja_id},
        )
        return [r.estado for r in rows]

    # --- feature 007: tiempo de cobro ---
    async def listar_cajas(self, tienda_id: int | None = None) -> list[dict]:
        """Cajas de la red o de una tienda — para el selector de la revisión
        semanal de tiempo de cobro (`cajas` no tiene modelo ORM, es referencia)."""
        cond = "" if tienda_id is None else "WHERE tienda_id = :t"
        rows = await self.session.execute(
            text(
                f"SELECT caja_id, tienda_id, nombre, activa FROM cajas {cond} "
                "ORDER BY tienda_id, caja_id"
            ),
            {"t": tienda_id},
        )
        return [dict(r._mapping) for r in rows]

    async def cajeros_de_caja(self, caja_id: int) -> list[int]:
        """Los cajeros que han abierto esta caja (research: `ventas` no tiene
        `caja_id`, el vínculo caja↔cajero vive en `apertura_caja` de 006)."""
        rows = await self.session.execute(
            text("SELECT DISTINCT cajero_id FROM apertura_caja WHERE caja_id = :c"),
            {"c": caja_id},
        )
        return [r.cajero_id for r in rows]

    async def ventas_tiempo_cobro(
        self, *, cajero_ids: list[int] | None = None, tienda_id: int | None = None,
        semana: int | None = None, anio: int | None = None,
    ) -> list[dict]:
        """Ventas con `fecha_inicio_cobro` registrada (excluye las sembradas y las
        previas a 007). El filtro de anuladas lo aplica la lógica pura."""
        cond = ["v.fecha_inicio_cobro IS NOT NULL"]
        params: dict = {}
        if cajero_ids is not None:
            cond.append("v.cajero_id = ANY(:cajeros)")
            params["cajeros"] = cajero_ids or [-1]
        if tienda_id is not None:
            cond.append("v.tienda_id = :tienda")
            params["tienda"] = tienda_id
        if semana is not None:
            cond.append("v.semana = :sem")
            params["sem"] = semana
        if anio is not None:
            cond.append("EXTRACT(YEAR FROM v.fecha_hora)::int = :anio")
            params["anio"] = anio
        rows = await self.session.execute(
            text(
                "SELECT v.venta_id, v.tienda_id, v.fecha_inicio_cobro, v.fecha_hora, v.estado "
                f"FROM ventas v WHERE {' AND '.join(cond)}"
            ),
            params,
        )
        return [dict(r._mapping) for r in rows]

    async def ventas_tiempo_cobro_mes(self, mes: int, anio: int) -> list[dict]:
        rows = await self.session.execute(
            text("""
                SELECT v.venta_id, v.tienda_id, v.fecha_inicio_cobro, v.fecha_hora, v.estado
                FROM ventas v
                WHERE v.fecha_inicio_cobro IS NOT NULL
                  AND EXTRACT(MONTH FROM v.fecha_hora)::int = :mes
                  AND EXTRACT(YEAR FROM v.fecha_hora)::int = :anio
            """),
            {"mes": mes, "anio": anio},
        )
        return [dict(r._mapping) for r in rows]

    async def rol_de_empleado(self, empleado_id: int) -> str | None:
        """Rol RBAC del empleado vía `usuarios.role_id → roles.nombre` (feature 003,
        research.md §4). `None` si el empleado no tiene usuario / rol asociado."""
        from sqlalchemy import text

        return await self.session.scalar(
            text(
                "SELECT r.nombre FROM usuarios u JOIN roles r ON r.role_id = u.role_id "
                "WHERE u.empleado_id = :e"
            ),
            {"e": empleado_id},
        )

    async def cantidad_devuelta(self, venta_id: int, product_id: int) -> int:
        from src.models.devolucion import Devolucion

        stmt = select(func.coalesce(func.sum(Devolucion.cantidad), 0)).where(
            Devolucion.venta_id == venta_id, Devolucion.product_id == product_id
        )
        return int(await self.session.scalar(stmt) or 0)

    # --- escrituras genéricas del agregado venta ---
    def agregar(self, entity) -> None:
        self.session.add(entity)

    async def flush(self) -> None:
        await self.session.flush()

    # --- pagos con tarjeta ---
    async def intentos_tarjeta(self, venta_id: int) -> list[IntentoPagoTarjeta]:
        stmt = (
            select(IntentoPagoTarjeta)
            .where(IntentoPagoTarjeta.venta_id == venta_id)
            .order_by(IntentoPagoTarjeta.intento_id)
        )
        return list((await self.session.scalars(stmt)).all())

    async def tiene_intento_aprobado(self, venta_id: int) -> bool:
        stmt = select(IntentoPagoTarjeta.intento_id).where(
            IntentoPagoTarjeta.venta_id == venta_id,
            IntentoPagoTarjeta.resultado == "aprobado",
        )
        return (await self.session.scalars(stmt)).first() is not None
