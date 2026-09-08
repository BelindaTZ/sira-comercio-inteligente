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
from src.models.inventario import Inventario
from src.models.lote import Lote
from src.models.merma import Merma
from src.models.orden_compra import OrdenCompra
from src.models.producto import Producto
from src.models.stock_maximo_categoria import StockMaximoCategoria
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
            WHERE {where}
        """
        estado_expr = """
            CASE
                WHEN i.cantidad_disponible <= i.cantidad_minima THEN 'quiebre'
                WHEN lote.fecha_vencimiento IS NOT NULL
                     AND lote.fecha_vencimiento <= CURRENT_DATE + 7 THEN 'por_vencer'
                WHEN i.cantidad_maxima IS NOT NULL
                     AND i.cantidad_disponible > i.cantidad_maxima THEN 'sobre_stock'
                ELSE 'normal'
            END
        """
        having = ""
        if estado in {"quiebre", "por_vencer", "sobre_stock", "normal"}:
            having = f" AND {estado_expr.strip()} = :estado"
            params["estado"] = estado
            base = base + having

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
                   u.pasillo, u.gondola,
                   lote.codigo_lote_proveedor AS lote_urgente,
                   lote.fecha_vencimiento,
                   CASE WHEN lote.fecha_vencimiento IS NOT NULL
                        THEN (lote.fecha_vencimiento - CURRENT_DATE) END AS dias_para_vencer,
                   {estado_expr} AS estado
            {base}
            ORDER BY
                CASE {estado_expr}
                     WHEN 'quiebre' THEN 0 WHEN 'por_vencer' THEN 1
                     WHEN 'sobre_stock' THEN 2 ELSE 3 END,
                p.nombre
            OFFSET :offset LIMIT :limit
            """),
            params,
        )
        return [dict(r._mapping) for r in filas], int(total)

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
