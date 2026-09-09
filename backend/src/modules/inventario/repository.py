"""InventarioRepository (T038) — acceso a datos de lotes, recepciones, ajustes,
mermas, inventario y movimientos. Sin lógica de negocio (Principio XI).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.alerta_inventario import AlertaInventario
from src.models.configuracion_inventario import ConfiguracionInventario
from src.models.empleado import Empleado
from src.models.inventario import Inventario
from src.models.lote import Lote
from src.models.merma import Merma
from src.models.orden_compra import OrdenCompra
from src.models.producto import Producto
from src.models.stock_maximo_categoria import StockMaximoCategoria
from src.models.ubicacion_producto import UbicacionProducto
from src.models.venta import Venta
from src.models.venta_detalle import VentaDetalle
from src.models.verificacion_anaquel import VerificacionAnaquel
from src.shared.repository import BaseRepository


def _filtrar_por_producto(stmt: Select, col_product_id, search: str | None) -> Select:
    """Filtra un `select(...)` por id de producto (si `search` es numérico) o por
    nombre/tipo/marca del producto (ILIKE). `col_product_id` es la columna
    `product_id` de la entidad seleccionada (Lote o AlertaInventario)."""
    if not search or not search.strip():
        return stmt
    termino = search.strip()
    if termino.isdigit():
        return stmt.where(col_product_id == int(termino))
    patron = f"%{termino}%"
    return stmt.join(Producto, Producto.product_id == col_product_id).where(
        or_(
            Producto.nombre.ilike(patron),
            Producto.product_type.ilike(patron),
            Producto.marca.ilike(patron),
        )
    )


class InventarioRepository(BaseRepository[Lote]):
    model = Lote

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # --- genérico ---
    def agregar(self, entity) -> None:
        self.session.add(entity)

    async def flush(self) -> None:
        await self.session.flush()

    async def refrescar(self, entity) -> None:
        await self.session.refresh(entity)

    # --- productos / órdenes ---
    async def get_producto(self, product_id: int) -> Producto | None:
        return await self.session.get(Producto, product_id)

    async def get_orden_for_update(self, orden_id: int) -> OrdenCompra | None:
        stmt = select(OrdenCompra).where(OrdenCompra.orden_id == orden_id).with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def lineas_sin_recibir(self, orden_id: int) -> int:
        """Cuántas líneas de la orden aún no tienen ninguna recepción registrada —
        la orden pasa a `recibida` sólo cuando todas se recibieron (permite
        recepción por partes de una orden multiproducto)."""
        return await self.session.scalar(
            text("""
                SELECT count(*) FROM orden_compra_detalle d
                WHERE d.orden_id = :o
                  AND NOT EXISTS (
                      SELECT 1 FROM recepcion_mercaderia rm
                      JOIN lotes l ON l.lote_id = rm.lote_id
                      WHERE rm.orden_id = :o AND l.product_id = d.product_id
                  )
            """),
            {"o": orden_id},
        )

    # --- inventario ---
    async def get_inventario_for_update(self, product_id: int, tienda_id: int) -> Inventario | None:
        stmt = (
            select(Inventario)
            .where(Inventario.product_id == product_id, Inventario.tienda_id == tienda_id)
            .with_for_update()
        )
        return (await self.session.scalars(stmt)).first()

    async def upsert_inventario(self, product_id: int, tienda_id: int, delta: int) -> Inventario:
        inv = await self.get_inventario_for_update(product_id, tienda_id)
        if inv is None:
            inv = Inventario(
                product_id=product_id,
                tienda_id=tienda_id,
                cantidad_disponible=max(0, delta),
            )
            self.session.add(inv)
            await self.session.flush()
        else:
            inv.cantidad_disponible += delta
        return inv

    # --- lotes ---
    async def get_lote_for_update(self, lote_id: int) -> Lote | None:
        stmt = select(Lote).where(Lote.lote_id == lote_id).with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def lotes_con_saldo_for_update(self, product_id: int, tienda_id: int) -> list[Lote]:
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

    def lotes_query(
        self,
        *,
        product_id: int | None = None,
        tienda_id: int | None = None,
        vence_antes_de: object | None = None,
        search: str | None = None,
    ) -> Select:
        stmt = select(Lote)
        if product_id is not None:
            stmt = stmt.where(Lote.product_id == product_id)
        if tienda_id is not None:
            stmt = stmt.where(Lote.tienda_id == tienda_id)
        if vence_antes_de is not None:
            stmt = stmt.where(Lote.fecha_vencimiento <= vence_antes_de)
        return _filtrar_por_producto(stmt, Lote.product_id, search)

    async def nombres_de_productos(self, ids: list[int]) -> dict[int, str | None]:
        if not ids:
            return {}
        rows = await self.session.execute(
            select(Producto.product_id, Producto.nombre).where(Producto.product_id.in_(ids))
        )
        return {pid: nombre for pid, nombre in rows}

    async def stock_por_sku(
        self,
        *,
        tienda_id: int,
        search: str | None,
        categoria: str | None,
        estado: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        """Vista de la pantalla de Inventario: una fila por SKU con stock vs.
        mínimo, ubicación en sala y el lote más próximo a vencer. `estado` se
        deriva en SQL (quiebre / por_vencer / sobre_stock / normal)."""
        cond = ["i.tienda_id = :tienda_id"]
        params: dict = {"tienda_id": tienda_id, "offset": offset, "limit": limit}
        if search and search.strip():
            t = search.strip()
            if t.isdigit():
                cond.append("p.product_id = :pid")
                params["pid"] = int(t)
            else:
                cond.append(
                    "(p.nombre ILIKE :q OR p.product_type ILIKE :q OR p.marca ILIKE :q)"
                )
                params["q"] = f"%{t}%"
        if categoria:
            cond.append("p.product_category = :categoria")
            params["categoria"] = categoria
        where = " AND ".join(cond)

        base = f"""
            FROM inventario i
            JOIN productos p ON p.product_id = i.product_id
            LEFT JOIN ubicacion_producto u
                   ON u.product_id = i.product_id AND u.tienda_id = i.tienda_id
            LEFT JOIN LATERAL (
                SELECT l.codigo_lote_proveedor, l.fecha_vencimiento
                FROM lotes l
                WHERE l.product_id = i.product_id AND l.tienda_id = i.tienda_id
                  AND l.cantidad_disponible > 0
                ORDER BY l.fecha_vencimiento ASC NULLS LAST, l.lote_id ASC
                LIMIT 1
            ) lote ON true
            LEFT JOIN LATERAL (
                SELECT COALESCE(SUM(ocd.cantidad), 0) AS unidades
                FROM orden_compra_detalle ocd
                JOIN ordenes_compra oc ON oc.orden_id = ocd.orden_id
                WHERE ocd.product_id = i.product_id AND oc.tienda_id = i.tienda_id
                  AND oc.estado IN ('pendiente', 'aprobada')
            ) transito ON true
            WHERE {where}
        """
        estado_expr = """
            CASE
                WHEN i.cantidad_disponible <= i.cantidad_minima THEN 'quiebre'
                WHEN lote.fecha_vencimiento IS NOT NULL
                     AND lote.fecha_vencimiento < CURRENT_DATE THEN 'vencido'
                WHEN lote.fecha_vencimiento IS NOT NULL
                     AND lote.fecha_vencimiento <= CURRENT_DATE + 7 THEN 'por_vencer'
                WHEN i.cantidad_maxima IS NOT NULL
                     AND i.cantidad_disponible > i.cantidad_maxima THEN 'sobre_stock'
                ELSE 'normal'
            END
        """
        if estado in {"quiebre", "vencido", "por_vencer", "sobre_stock", "normal"}:
            params["estado"] = estado
            base = base + f" AND {estado_expr.strip()} = :estado"
        elif estado == "en_transito":
            base = base + " AND transito.unidades > 0"

        total = await self.session.scalar(text(f"SELECT count(*) {base}"), params) or 0
        filas = await self.session.execute(
            text(f"""
            SELECT p.product_id, p.nombre, p.marca, p.product_category,
                   p.clasificacion_abc, p.imagen_url, p.codigo_barras,
                   p.costo, p.precio_base, p.es_perecedero,
                   CASE WHEN p.precio_base > 0
                        THEN round((p.precio_base - COALESCE(p.costo, 0)) / p.precio_base * 100, 1)
                        END AS margen_pct,
                   i.cantidad_disponible, i.cantidad_minima, i.cantidad_maxima,
                   transito.unidades AS en_transito,
                   u.pasillo, u.gondola,
                   lote.codigo_lote_proveedor AS lote_urgente,
                   lote.fecha_vencimiento,
                   CASE WHEN lote.fecha_vencimiento IS NOT NULL
                        THEN (lote.fecha_vencimiento - CURRENT_DATE) END AS dias_para_vencer,
                   {estado_expr} AS estado
            {base}
            ORDER BY
                CASE {estado_expr}
                     WHEN 'quiebre' THEN 0 WHEN 'vencido' THEN 1 WHEN 'por_vencer' THEN 2
                     WHEN 'sobre_stock' THEN 3 ELSE 4 END,
                p.nombre
            OFFSET :offset LIMIT :limit
            """),
            params,
        )
        return [dict(r._mapping) for r in filas], int(total)

    async def resumen_stock(self, tienda_id: int) -> dict:
        """Contadores + tasa de merma del mes para la fila de KPIs."""
        row = await self.session.execute(
            text("""
            WITH s AS (
                SELECT
                    CASE
                        WHEN i.cantidad_disponible <= i.cantidad_minima THEN 'quiebre'
                        WHEN lote.fv IS NOT NULL AND lote.fv < CURRENT_DATE THEN 'vencido'
                        WHEN lote.fv IS NOT NULL AND lote.fv <= CURRENT_DATE + 7 THEN 'por_vencer'
                        WHEN i.cantidad_maxima IS NOT NULL
                             AND i.cantidad_disponible > i.cantidad_maxima THEN 'sobre_stock'
                        ELSE 'normal'
                    END AS estado
                FROM inventario i
                LEFT JOIN LATERAL (
                    SELECT min(l.fecha_vencimiento) AS fv FROM lotes l
                    WHERE l.product_id = i.product_id AND l.tienda_id = i.tienda_id
                      AND l.cantidad_disponible > 0
                ) lote ON true
                WHERE i.tienda_id = :t
            ),
            tr AS (
                SELECT COALESCE(SUM(ocd.cantidad), 0) AS unidades,
                       COUNT(DISTINCT oc.orden_id) AS ordenes
                FROM ordenes_compra oc
                JOIN orden_compra_detalle ocd ON ocd.orden_id = oc.orden_id
                WHERE oc.tienda_id = :t AND oc.estado IN ('pendiente', 'aprobada')
            ),
            mm AS (
                SELECT COALESCE(SUM(cantidad), 0) AS merma_uni
                FROM mermas
                WHERE tienda_id = :t AND estado_validacion = 'validada'
                  AND fecha >= date_trunc('month', CURRENT_DATE)
            ),
            oh AS (
                SELECT COALESCE(SUM(cantidad_disponible), 0) AS disponible
                FROM inventario WHERE tienda_id = :t
            )
            SELECT
                (SELECT count(*) FROM s) AS skus,
                (SELECT count(*) FROM s WHERE estado = 'quiebre') AS quiebre,
                (SELECT count(*) FROM s WHERE estado = 'vencido') AS vencido,
                (SELECT count(*) FROM s WHERE estado = 'por_vencer') AS por_vencer,
                (SELECT count(*) FROM s WHERE estado = 'sobre_stock') AS sobre_stock,
                (SELECT count(*) FROM s WHERE estado = 'normal') AS normal,
                tr.unidades AS unidades_transito, tr.ordenes AS ordenes_transito,
                CASE WHEN oh.disponible > 0
                     THEN round(mm.merma_uni::numeric / (oh.disponible + mm.merma_uni) * 100, 2)
                     ELSE 0 END AS tasa_merma_pct
            FROM tr, mm, oh
            """),
            {"t": tienda_id},
        )
        return dict(row.first()._mapping)

    async def upsert_ubicacion(
        self, *, product_id: int, tienda_id: int, pasillo: str, gondola, nivel, empleado_id: int
    ) -> dict:
        await self.session.execute(
            text("""
            INSERT INTO ubicacion_producto
                (product_id, tienda_id, pasillo, gondola, nivel, actualizado_por, updated_at)
            VALUES (:p, :t, :pasillo, :gondola, :nivel, :emp, CURRENT_TIMESTAMP)
            ON CONFLICT (product_id, tienda_id) DO UPDATE SET
                pasillo = EXCLUDED.pasillo, gondola = EXCLUDED.gondola,
                nivel = EXCLUDED.nivel, actualizado_por = EXCLUDED.actualizado_por,
                updated_at = CURRENT_TIMESTAMP
            """),
            {
                "p": product_id, "t": tienda_id, "pasillo": pasillo,
                "gondola": gondola, "nivel": nivel, "emp": empleado_id,
            },
        )
        row = await self.session.execute(
            text(
                "SELECT product_id, tienda_id, pasillo, gondola, nivel "
                "FROM ubicacion_producto WHERE product_id = :p AND tienda_id = :t"
            ),
            {"p": product_id, "t": tienda_id},
        )
        return dict(row.first()._mapping)

    async def buscar_productos(self, termino: str, limite: int = 12) -> list[Producto]:
        """Autocompletado para los formularios de operación (ajuste, merma,
        anaquel): por id exacto si es numérico, si no por nombre/tipo/marca."""
        t = (termino or "").strip()
        if not t:
            return []
        stmt = select(Producto).where(Producto.activo.is_(True))
        if t.isdigit():
            stmt = stmt.where(Producto.product_id == int(t))
        else:
            patron = f"%{t}%"
            stmt = stmt.where(
                or_(
                    Producto.nombre.ilike(patron),
                    Producto.product_type.ilike(patron),
                    Producto.marca.ilike(patron),
                )
            )
        stmt = stmt.order_by(Producto.nombre).limit(limite)
        return list((await self.session.scalars(stmt)).all())

    # --- mermas ---
    async def get_merma_for_update(self, merma_id: int) -> Merma | None:
        stmt = select(Merma).where(Merma.merma_id == merma_id).with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def listar_mermas(
        self,
        tienda_id: int | None = None,
        causa: str | None = None,
        estado_validacion: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        stmt = (
            select(
                Merma,
                Producto.nombre.label("product_nombre"),
                Producto.codigo_barras.label("product_sku"),
                Producto.product_category.label("product_categoria"),
                Producto.costo.label("costo_unitario"),
                Producto.imagen_url.label("imagen_url"),
                Lote.codigo_lote_proveedor.label("lote_numero"),
                Lote.fecha_vencimiento.label("lote_vencimiento"),
                Empleado.nombre.label("empleado_nombre"),
                UbicacionProducto.pasillo.label("ubic_pasillo"),
                UbicacionProducto.gondola.label("ubic_gondola"),
            )
            .join(Producto, Producto.product_id == Merma.product_id)
            .outerjoin(Lote, Lote.lote_id == Merma.lote_id)
            .outerjoin(Empleado, Empleado.empleado_id == Merma.empleado_id)
            .outerjoin(
                UbicacionProducto,
                (UbicacionProducto.product_id == Merma.product_id)
                & (UbicacionProducto.tienda_id == Merma.tienda_id),
            )
        )
        if tienda_id is not None:
            stmt = stmt.where(Merma.tienda_id == tienda_id)
        if causa:
            stmt = stmt.where(Merma.causa == causa)
        if estado_validacion:
            stmt = stmt.where(Merma.estado_validacion == estado_validacion)
        if search and search.strip():
            termino = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Producto.nombre.ilike(termino),
                    Producto.codigo_barras.ilike(termino),
                    Lote.codigo_lote_proveedor.ilike(termino),
                )
            )
        stmt = stmt.order_by(Merma.merma_id.desc()).limit(limit)
        rows = (await self.session.execute(stmt)).all()
        resultado = []
        for r in rows:
            m = r.Merma
            if r.ubic_pasillo:
                ubicacion = r.ubic_pasillo
                if r.ubic_gondola:
                    ubicacion = f"{r.ubic_pasillo} · {r.ubic_gondola}"
            else:
                ubicacion = None
            resultado.append({
                "merma_id": m.merma_id,
                "product_id": m.product_id,
                "tienda_id": m.tienda_id,
                "lote_id": m.lote_id,
                "cantidad": m.cantidad,
                "causa": m.causa,
                "valor": m.valor,
                "empleado_id": m.empleado_id,
                "fecha": m.fecha,
                "estado_validacion": m.estado_validacion,
                "empleado_valida_id": m.empleado_valida_id,
                "fecha_validacion": m.fecha_validacion,
                "destino": m.destino,
                "observaciones": m.observaciones,
                "product_nombre": r.product_nombre,
                "product_sku": r.product_sku,
                "product_categoria": r.product_categoria,
                "costo_unitario": r.costo_unitario,
                "imagen_url": r.imagen_url,
                "lote_numero": r.lote_numero,
                "lote_vencimiento": r.lote_vencimiento,
                "empleado_nombre": r.empleado_nombre,
                "ubicacion_sala": ubicacion,
            })
        return resultado

    async def kpis_merma(self, tienda_id: int) -> dict:
        stmt_mes = (
            select(
                func.coalesce(func.sum(Merma.valor), 0).label("total_valor"),
                func.count(Merma.merma_id).label("total_incidentes"),
                func.count(func.distinct(Merma.product_id)).label("skus_criticos"),
            )
            .where(
                Merma.tienda_id == tienda_id,
                Merma.fecha >= func.date_trunc("month", func.current_date()),
            )
        )
        res_mes = (await self.session.execute(stmt_mes)).first()
        total_valor = Decimal(str(res_mes.total_valor)) if res_mes else Decimal("0")
        skus_criticos = int(res_mes.skus_criticos) if res_mes else 0

        # Conteo de pendientes
        stmt_pend = (
            select(func.count(Merma.merma_id))
            .where(Merma.tienda_id == tienda_id, Merma.estado_validacion == "pendiente")
        )
        pendientes = int(await self.session.scalar(stmt_pend) or 0)

        # Desglose por causa
        stmt_causas = (
            select(
                Merma.causa,
                func.count(Merma.merma_id).label("cantidad"),
                func.coalesce(func.sum(Merma.valor), 0).label("valor"),
            )
            .where(
                Merma.tienda_id == tienda_id,
                Merma.fecha >= func.date_trunc("month", func.current_date()),
            )
            .group_by(Merma.causa)
        )
        causas_rows = (await self.session.execute(stmt_causas)).all()
        causas_dict = {}
        for c in causas_rows:
            causas_dict[c.causa] = {
                "cantidad": int(c.cantidad),
                "valor": Decimal(str(c.valor)),
            }

        # Recuperación real: valor de la merma del mes cuyo destino permite
        # aprovechar la unidad (donación a red de alimentos, devolución con nota
        # de crédito del proveedor). Destrucción y cuarentena no recuperan.
        stmt_recup = select(func.coalesce(func.sum(Merma.valor), 0)).where(
            Merma.tienda_id == tienda_id,
            Merma.fecha >= func.date_trunc("month", func.current_date()),
            Merma.destino.in_(("donacion", "devolucion")),
        )
        recuperacion_monto = Decimal(str(await self.session.scalar(stmt_recup) or 0))
        tasa_recuperacion_pct = (
            (recuperacion_monto / total_valor * Decimal("100")).quantize(Decimal("0.1"))
            if total_valor > 0
            else Decimal("0")
        )

        # Tasa de merma sobre venta: valor de merma del mes / venta confirmada del
        # mes en la misma tienda (ambos reales).
        stmt_venta = select(func.coalesce(func.sum(Venta.total), 0)).where(
            Venta.tienda_id == tienda_id,
            Venta.estado == "confirmada",
            Venta.fecha_hora >= func.date_trunc("month", func.current_date()),
        )
        venta_mes = Decimal(str(await self.session.scalar(stmt_venta) or 0))
        tasa_merma_pct = (
            (total_valor / venta_mes * Decimal("100")).quantize(Decimal("0.01"))
            if venta_mes > 0
            else Decimal("0")
        )

        return {
            "merma_acumulada_mes": total_valor,
            "tasa_merma_pct": tasa_merma_pct,
            "venta_mes": venta_mes,
            "skus_criticos_count": skus_criticos,
            "tasa_recuperacion_pct": tasa_recuperacion_pct,
            "recuperacion_monto": recuperacion_monto,
            "pendientes_count": pendientes,
            "causas_desglose": causas_dict,
        }

    # --- US3: configuración ---
    async def config(self, clave: str, defecto: Decimal) -> Decimal:
        valor = await self.session.scalar(
            select(ConfiguracionInventario.valor).where(ConfiguracionInventario.clave == clave)
        )
        return Decimal(str(valor)) if valor is not None else defecto

    # --- US3: demanda / reposición ---
    async def unidades_vendidas(self, product_id: int, tienda_id: int, desde: datetime) -> int:
        stmt = (
            select(func.coalesce(func.sum(VentaDetalle.cantidad), 0))
            .select_from(VentaDetalle)
            .join(Venta, Venta.venta_id == VentaDetalle.venta_id)
            .where(
                VentaDetalle.product_id == product_id,
                Venta.tienda_id == tienda_id,
                Venta.estado == "confirmada",
                Venta.fecha_hora >= desde,
            )
        )
        return int(await self.session.scalar(stmt) or 0)

    async def pares_inventario(self, tienda_id: int | None = None) -> list[tuple[int, int]]:
        stmt = select(Inventario.product_id, Inventario.tienda_id)
        if tienda_id is not None:
            stmt = stmt.where(Inventario.tienda_id == tienda_id)
        return [(r[0], r[1]) for r in (await self.session.execute(stmt)).all()]

    # --- US3: alertas ---
    async def alerta_pendiente(
        self, product_id: int, tienda_id: int, tipo: str
    ) -> AlertaInventario | None:
        stmt = select(AlertaInventario).where(
            AlertaInventario.product_id == product_id,
            AlertaInventario.tienda_id == tienda_id,
            AlertaInventario.tipo == tipo,
            AlertaInventario.estado == "pendiente",
        )
        return (await self.session.scalars(stmt)).first()

    async def alerta_vencimiento_pendiente_lote(self, lote_id: int) -> bool:
        stmt = select(AlertaInventario.alerta_id).where(
            AlertaInventario.lote_id == lote_id,
            AlertaInventario.tipo == "vencimiento",
            AlertaInventario.estado == "pendiente",
        )
        return (await self.session.scalars(stmt)).first() is not None

    async def get_alerta_for_update(self, alerta_id: int) -> AlertaInventario | None:
        stmt = (
            select(AlertaInventario)
            .where(AlertaInventario.alerta_id == alerta_id)
            .with_for_update()
        )
        return (await self.session.scalars(stmt)).first()

    def alertas_query(
        self,
        *,
        tipo: str | None = None,
        estado: str | None = None,
        tienda_id: int | None = None,
        search: str | None = None,
    ) -> Select:
        stmt = select(AlertaInventario)
        if tipo is not None:
            stmt = stmt.where(AlertaInventario.tipo == tipo)
        if estado is not None:
            stmt = stmt.where(AlertaInventario.estado == estado)
        if tienda_id is not None:
            stmt = stmt.where(AlertaInventario.tienda_id == tienda_id)
        return _filtrar_por_producto(stmt, AlertaInventario.product_id, search)

    async def lotes_perecederos_venciendo(
        self, umbral: date, tienda_id: int | None = None
    ) -> list[Lote]:
        stmt = (
            select(Lote)
            .join(Producto, Producto.product_id == Lote.product_id)
            .where(
                Producto.es_perecedero.is_(True),
                Lote.fecha_vencimiento.is_not(None),
                Lote.fecha_vencimiento <= umbral,
                Lote.cantidad_disponible > 0,
            )
            .order_by(Lote.fecha_vencimiento.asc())
        )
        if tienda_id is not None:
            stmt = stmt.where(Lote.tienda_id == tienda_id)
        return list((await self.session.scalars(stmt)).all())

    # --- US3: stock máximo por categoría ---
    async def get_stock_maximo(
        self, product_category: str, tienda_id: int
    ) -> StockMaximoCategoria | None:
        stmt = select(StockMaximoCategoria).where(
            StockMaximoCategoria.product_category == product_category,
            StockMaximoCategoria.tienda_id == tienda_id,
        )
        return (await self.session.scalars(stmt)).first()

    def stock_maximo_query(self, *, tienda_id: int, product_category: str | None = None) -> Select:
        stmt = select(StockMaximoCategoria).where(StockMaximoCategoria.tienda_id == tienda_id)
        if product_category is not None:
            stmt = stmt.where(StockMaximoCategoria.product_category == product_category)
        return stmt

    # --- US3: verificación de anaquel ---
    async def get_verificacion_anaquel(
        self, product_id: int, tienda_id: int, fecha: date
    ) -> VerificacionAnaquel | None:
        stmt = select(VerificacionAnaquel).where(
            VerificacionAnaquel.product_id == product_id,
            VerificacionAnaquel.tienda_id == tienda_id,
            VerificacionAnaquel.fecha == fecha,
        )
        return (await self.session.scalars(stmt)).first()
