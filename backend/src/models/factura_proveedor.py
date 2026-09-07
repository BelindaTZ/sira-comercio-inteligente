from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

FACTURA_ESTADOS = ("pendiente", "pagada_parcial", "pagada", "vencida")


class FacturaProveedor(Base):
    """`facturas_proveedor` (FR-033) — tercer elemento del 3-way match. Único
    `(orden_id, numero_factura)`; solo contra una orden ya `recibida`. `estado` lo
    recalcula la capa de servicio al confirmar cada pago (FR-035), no un trigger."""

    __tablename__ = "facturas_proveedor"

    factura_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    orden_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ordenes_compra.orden_id"), nullable=False
    )
    numero_factura: Mapped[str] = mapped_column(String(50), nullable=False)
    monto_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    empleado_registra_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
