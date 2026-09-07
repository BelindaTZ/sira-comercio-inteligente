from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

MERMA_CAUSAS = ("caducidad", "robo", "rotura", "error_humano")
MERMA_ESTADOS = ("pendiente", "validada", "rechazada")


class Merma(Base):
    """`mermas` (FR-018/FR-019) — `causa` es lista cerrada. `estado_validacion`,
    `lote_id`, `empleado_valida_id`, `fecha_validacion` agregados en la ronda 8
    (spec Key Entities → Merma). El stock se descuenta al validar, no al registrar."""

    __tablename__ = "mermas"

    merma_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    lote_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("lotes.lote_id"))
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    causa: Mapped[str] = mapped_column(String(20), nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    empleado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    estado_validacion: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    empleado_valida_id: Mapped[int | None] = mapped_column(Integer)
    fecha_validacion: Mapped[datetime | None] = mapped_column(DateTime)
