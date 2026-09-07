from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

RESULTADO_PAGO = ("aprobado", "rechazado", "error_tecnico")


class IntentoPagoTarjeta(Base):
    """`intentos_pago_tarjeta` (FR-030/FR-031) — `resultado` distingue
    explícitamente rechazo del banco de error técnico de la pasarela."""

    __tablename__ = "intentos_pago_tarjeta"

    intento_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ventas.venta_id", ondelete="CASCADE"), nullable=False
    )
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    referencia_pasarela: Mapped[str | None] = mapped_column(String(100))
    monto: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
