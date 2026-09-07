"""VentasRepository (T023) — acceso a datos de `ventas` / `venta_detalle` y los
efectos de una venta sobre el inventario (lotes, movimientos). Sin lógica de
negocio (Principio XI): sólo consultas y escrituras.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
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
