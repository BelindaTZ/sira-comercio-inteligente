"""ComprasRepository (T054) — proveedores, órdenes de compra, facturas y pagos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.factura_proveedor import FacturaProveedor
from src.models.inventario import Inventario
from src.models.orden_compra import OrdenCompra
from src.models.orden_compra_detalle import OrdenCompraDetalle
from src.models.pago_proveedor import PagoProveedor
from src.models.producto import Producto
from src.models.proveedor import Proveedor
from src.shared.repository import BaseRepository


class ComprasRepository(BaseRepository[OrdenCompra]):
    model = OrdenCompra

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    def agregar(self, entity) -> None:
        self.session.add(entity)

    async def flush(self) -> None:
        await self.session.flush()

    # --- proveedores ---
    async def get_proveedor(self, proveedor_id: int) -> Proveedor | None:
        return await self.session.get(Proveedor, proveedor_id)

    def proveedores_query(self) -> Select:
        return select(Proveedor).order_by(Proveedor.nombre)

    async def listar_proveedores(self, *, solo_activos: bool = True) -> list[Proveedor]:
        stmt = select(Proveedor).order_by(Proveedor.nombre)
        if solo_activos:
            stmt = stmt.where(Proveedor.activo.is_(True))
        return list((await self.session.scalars(stmt)).all())

    # --- órdenes ---
    async def get_orden_for_update(self, orden_id: int) -> OrdenCompra | None:
        stmt = select(OrdenCompra).where(OrdenCompra.orden_id == orden_id).with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def lineas_de_orden(self, orden_id: int) -> list[OrdenCompraDetalle]:
        stmt = (
            select(OrdenCompraDetalle)
            .where(OrdenCompraDetalle.orden_id == orden_id)
            .order_by(OrdenCompraDetalle.orden_detalle_id)
        )
        return list((await self.session.scalars(stmt)).all())

    async def listar_ordenes(
        self,
        *,
        tienda_id: int | None = None,
        estado: str | None = None,
        limit: int = 50,
    ) -> list[OrdenCompra]:
        stmt = select(OrdenCompra)
        if tienda_id is not None:
            stmt = stmt.where(OrdenCompra.tienda_id == tienda_id)
        if estado is not None:
            stmt = stmt.where(OrdenCompra.estado == estado)
        stmt = stmt.order_by(OrdenCompra.orden_id.desc()).limit(limit)
        return list((await self.session.scalars(stmt)).all())

    async def get_producto(self, product_id: int) -> Producto | None:
        return await self.session.get(Producto, product_id)

    async def productos_de_proveedor(self, proveedor_id: int) -> list[dict]:
        """FR-044: productos que este proveedor ha suministrado, del historial real
        de `ordenes_compra`/`orden_compra_detalle` (sin catálogo maestro nuevo)."""
        stmt = (
            select(
                OrdenCompraDetalle.product_id,
                Producto.nombre,
                Producto.product_category,
                func.count(func.distinct(OrdenCompra.orden_id)).label("ordenes"),
                func.sum(OrdenCompraDetalle.cantidad).label("cantidad_total"),
                func.max(OrdenCompra.fecha).label("ultima_fecha"),
            )
            .select_from(OrdenCompraDetalle)
            .join(OrdenCompra, OrdenCompra.orden_id == OrdenCompraDetalle.orden_id)
            .join(Producto, Producto.product_id == OrdenCompraDetalle.product_id, isouter=True)
            .where(OrdenCompra.proveedor_id == proveedor_id)
            .group_by(OrdenCompraDetalle.product_id, Producto.nombre, Producto.product_category)
            .order_by(func.max(OrdenCompra.fecha).desc())
        )
        return [dict(r._mapping) for r in (await self.session.execute(stmt)).all()]

    async def proveedores_de_producto(self, product_id: int) -> list[dict]:
        stmt = (
            select(
                OrdenCompra.proveedor_id,
                Proveedor.nombre,
                Proveedor.ruc,
                func.count(func.distinct(OrdenCompra.orden_id)).label("ordenes"),
                func.sum(OrdenCompraDetalle.cantidad).label("cantidad_total"),
                func.max(OrdenCompra.fecha).label("ultima_fecha"),
            )
            .select_from(OrdenCompraDetalle)
            .join(OrdenCompra, OrdenCompra.orden_id == OrdenCompraDetalle.orden_id)
            .join(Proveedor, Proveedor.proveedor_id == OrdenCompra.proveedor_id, isouter=True)
            .where(OrdenCompraDetalle.product_id == product_id)
            .group_by(OrdenCompra.proveedor_id, Proveedor.nombre, Proveedor.ruc)
            .order_by(func.max(OrdenCompra.fecha).desc())
        )
        return [dict(r._mapping) for r in (await self.session.execute(stmt)).all()]

    async def ultimo_proveedor_de(self, product_id: int, tienda_id: int) -> int | None:
        stmt = (
            select(OrdenCompra.proveedor_id)
            .join(OrdenCompraDetalle, OrdenCompraDetalle.orden_id == OrdenCompra.orden_id)
            .where(
                OrdenCompraDetalle.product_id == product_id,
                OrdenCompra.tienda_id == tienda_id,
            )
            .order_by(OrdenCompra.orden_id.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def productos_bajo_punto(self, tienda_id: int) -> list[Inventario]:
        stmt = select(Inventario).where(
            Inventario.tienda_id == tienda_id,
            Inventario.cantidad_minima > 0,
            Inventario.cantidad_disponible < Inventario.cantidad_minima,
        )
        return list((await self.session.scalars(stmt)).all())

    async def contar_ordenes_por_tipo(self, desde: date, hasta: date) -> dict[str, int]:
        stmt = (
            select(OrdenCompra.tipo, func.count())
            .where(OrdenCompra.fecha >= desde, OrdenCompra.fecha < hasta)
            .group_by(OrdenCompra.tipo)
        )
        return {row[0]: int(row[1]) for row in (await self.session.execute(stmt)).all()}

    # --- facturas ---
    async def get_factura_for_update(self, factura_id: int) -> FacturaProveedor | None:
        stmt = (
            select(FacturaProveedor)
            .where(FacturaProveedor.factura_id == factura_id)
            .with_for_update()
        )
        return (await self.session.scalars(stmt)).first()

    async def factura_existe(self, orden_id: int, numero_factura: str) -> bool:
        stmt = select(FacturaProveedor.factura_id).where(
            FacturaProveedor.orden_id == orden_id,
            FacturaProveedor.numero_factura == numero_factura,
        )
        return (await self.session.scalars(stmt)).first() is not None

    async def pagado_de_factura(self, factura_id: int) -> Decimal:
        total = await self.session.scalar(
            select(func.coalesce(func.sum(PagoProveedor.monto), 0)).where(
                PagoProveedor.factura_id == factura_id
            )
        )
        return Decimal(str(total or 0))

    def facturas_query(
        self,
        *,
        estado: str | None = None,
        vencimiento_antes: date | None = None,
    ) -> Select:
        stmt = select(FacturaProveedor)
        if estado is not None:
            stmt = stmt.where(FacturaProveedor.estado == estado)
        if vencimiento_antes is not None:
            stmt = stmt.where(FacturaProveedor.fecha_vencimiento <= vencimiento_antes)
        return stmt

    async def facturas_abiertas_en(self, desde: date, hasta: date) -> list[FacturaProveedor]:
        stmt = select(FacturaProveedor).where(
            FacturaProveedor.estado.in_(("pendiente", "pagada_parcial", "vencida")),
            FacturaProveedor.fecha_emision >= desde,
            FacturaProveedor.fecha_emision <= hasta,
        )
        return list((await self.session.scalars(stmt)).all())

    # --- medios de pago ---
    async def medio_pago_existe(self, medio_pago_id: int) -> bool:
        from src.models.medio_pago import MedioPago

        return (await self.session.get(MedioPago, medio_pago_id)) is not None
