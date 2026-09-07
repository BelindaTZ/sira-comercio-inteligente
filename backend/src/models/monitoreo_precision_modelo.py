from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class MonitoreoPrecisionModelo(Base):
    """`monitoreo_precision_modelo` (feature 004, FR-011/FR-013) — WAPE semanal del
    modelo vigente contra la demanda real ya observada. Su histórico por modelo
    permite ver tendencia, no sólo el último valor."""

    __tablename__ = "monitoreo_precision_modelo"
    __table_args__ = (UniqueConstraint("modelo_id", "semana", "anio"),)

    monitoreo_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    modelo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("modelo_demanda.modelo_id", ondelete="CASCADE"), nullable=False
    )
    semana: Mapped[int] = mapped_column(Integer, nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    metrica_precision: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    supero_umbral_alerta: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fecha_calculo: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
