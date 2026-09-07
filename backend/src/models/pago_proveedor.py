from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class PagoProveedor(Base):
    """`pagos_proveedor` (FR-034) — CHECK de doble persona
    (`empleado_registra_id <> empleado_autoriza_id`), sin excepción por monto."""

    __tablename__ = "pagos_proveedor"
    __table_args__ = (
        CheckConstraint(
            "empleado_registra_id <> empleado_autoriza_id",
            name="chk_pago_proveedor_doble_persona",
        ),
    )

    pago_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    factura_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("facturas_proveedor.factura_id"), nullable=False
    )
    monto: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    medio_pago_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("medios_pago.medio_pago_id"), nullable=False
    )
    referencia: Mapped[str | None] = mapped_column(String(100))
    empleado_registra_id: Mapped[int] = mapped_column(Integer, nullable=False)
    empleado_autoriza_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
