from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

ESTADOS_REGLA = ("vigente", "reemplazada", "desactivada")


class ReglaAfinidad(Base):
    """`regla_afinidad` (feature 005) — regla de asociación antecedente→consecuente
    con su soporte/confianza/lift (research.md Decisión 1). Sólo las `vigente` se
    evalúan para la recomendación en punto de venta y el cupón de afinidad."""

    __tablename__ = "regla_afinidad"

    regla_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id_antecedente: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id_consecuente: Mapped[int] = mapped_column(Integer, nullable=False)
    soporte: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    confianza: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    lift: Mapped[float | None] = mapped_column(Numeric(10, 4))
    fecha_calculo: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="vigente")
    desactivada_por: Mapped[int | None] = mapped_column(Integer)
    fecha_desactivacion: Mapped[datetime | None] = mapped_column(DateTime)
    motivo_desactivacion: Mapped[str | None] = mapped_column(String(300))
