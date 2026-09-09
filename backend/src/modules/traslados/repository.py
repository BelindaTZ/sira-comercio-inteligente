"""TrasladosRepository — acceso a datos de `traslados_stock` y de la
disponibilidad de stock por sucursal. Sin lógica de negocio (Principio XI).

Las mutaciones de `inventario` / `lotes` / `movimientos_inventario` del despacho y
la recepción se hacen a través de `InventarioRepository` (001), reutilizado por el
servicio — no se duplica ese mecanismo aquí (Principio VIII).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.traslado_stock import TrasladoStock


class TrasladosRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def agregar(self, entity) -> None:
        self.session.add(entity)

    async def flush(self) -> None:
        await self.session.flush()

    async def refrescar(self, entity) -> None:
        await self.session.refresh(entity)

    # ------------------------------------------------------------ disponibilidad (US1)
    async def disponibilidad_sucursales(self, product_id: int) -> list[dict]:
        """Stock disponible del producto en cada tienda activa de la red (0 si la
        tienda no tiene fila de inventario para ese producto)."""
        rows = await self.session.execute(
            text("""
                SELECT t.tienda_id,
                       t.nombre AS nombre_tienda,
                       COALESCE(i.cantidad_disponible, 0) AS cantidad_disponible
                FROM tiendas t
                LEFT JOIN inventario i
                       ON i.tienda_id = t.tienda_id AND i.product_id = :pid
                WHERE t.activa = true
                ORDER BY t.tienda_id
            """),
            {"pid": product_id},
        )
        return [dict(r._mapping) for r in rows]

    async def disponibilidad_por_producto(self, product_ids: list[int]) -> dict[int, list[dict]]:
        """Igual que `disponibilidad_sucursales` pero para varios productos a la vez
        (usado por la sugerencia de compra extendida, FR-002)."""
        if not product_ids:
            return {}
        rows = await self.session.execute(
            text("""
                SELECT p.product_id,
                       t.tienda_id,
                       t.nombre AS nombre_tienda,
                       COALESCE(i.cantidad_disponible, 0) AS cantidad_disponible
                FROM (SELECT unnest(CAST(:pids AS int[])) AS product_id) p
                CROSS JOIN tiendas t
                LEFT JOIN inventario i
                       ON i.tienda_id = t.tienda_id AND i.product_id = p.product_id
                WHERE t.activa = true
                ORDER BY p.product_id, t.tienda_id
            """),
            {"pids": list(product_ids)},
        )
        agrupado: dict[int, list[dict]] = {}
        for r in rows:
            m = dict(r._mapping)
            agrupado.setdefault(m.pop("product_id"), []).append(m)
        return agrupado

    async def tiendas_activas(self) -> list[dict]:
        """Sucursales activas de la red — para los selectores de origen/destino."""
        rows = await self.session.execute(
            text(
                "SELECT tienda_id, codigo, nombre, ciudad FROM tiendas "
                "WHERE activa = true ORDER BY nombre"
            )
        )
        return [dict(r._mapping) for r in rows]

    async def nombres_tiendas(self, ids: set[int]) -> dict[int, str]:
        if not ids:
            return {}
        rows = await self.session.execute(
            text("SELECT tienda_id, nombre FROM tiendas WHERE tienda_id = ANY(:ids)"),
            {"ids": list(ids)},
        )
        return {r.tienda_id: r.nombre for r in rows}

    async def nombres_empleados(self, ids: set[int]) -> dict[int, str]:
        ids = {i for i in ids if i is not None}
        if not ids:
            return {}
        rows = await self.session.execute(
            text("SELECT empleado_id, nombre FROM empleados WHERE empleado_id = ANY(:ids)"),
            {"ids": list(ids)},
        )
        return {r.empleado_id: r.nombre for r in rows}

    async def nombres_productos(self, ids: set[int]) -> dict[int, str]:
        if not ids:
            return {}
        rows = await self.session.execute(
            text("SELECT product_id, nombre FROM productos WHERE product_id = ANY(:ids)"),
            {"ids": list(ids)},
        )
        return {r.product_id: r.nombre for r in rows}

    # ------------------------------------------------------------ traslados_stock
    async def get(self, traslado_id: int) -> TrasladoStock | None:
        return await self.session.get(TrasladoStock, traslado_id)

    async def get_for_update(self, traslado_id: int) -> TrasladoStock | None:
        stmt = (
            select(TrasladoStock).where(TrasladoStock.traslado_id == traslado_id).with_for_update()
        )
        return (await self.session.scalars(stmt)).first()

    async def crear(self, traslado: TrasladoStock) -> TrasladoStock:
        self.session.add(traslado)
        await self.session.flush()
        await self.session.refresh(traslado)
        return traslado

    async def listar(
        self,
        *,
        estado: str | None = None,
        tienda_origen_id: int | None = None,
        tienda_destino_id: int | None = None,
    ) -> list[TrasladoStock]:
        stmt = select(TrasladoStock)
        if estado is not None:
            stmt = stmt.where(TrasladoStock.estado == estado)
        if tienda_origen_id is not None:
            stmt = stmt.where(TrasladoStock.tienda_origen_id == tienda_origen_id)
        if tienda_destino_id is not None:
            stmt = stmt.where(TrasladoStock.tienda_destino_id == tienda_destino_id)
        stmt = stmt.order_by(TrasladoStock.fecha_hora.desc(), TrasladoStock.traslado_id.desc())
        return list((await self.session.scalars(stmt)).all())

    async def listar_periodo(self, desde: date, hasta: date) -> list[TrasladoStock]:
        stmt = (
            select(TrasladoStock)
            .where(
                func.date(TrasladoStock.fecha_hora) >= desde,
                func.date(TrasladoStock.fecha_hora) <= hasta,
            )
            .order_by(TrasladoStock.fecha_hora.asc(), TrasladoStock.traslado_id.asc())
        )
        return list((await self.session.scalars(stmt)).all())
