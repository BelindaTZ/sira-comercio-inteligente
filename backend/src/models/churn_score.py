from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

CHURN_SEVERIDADES = ("en_riesgo", "inactivo")


class ChurnScore(Base):
    """`churn_score` — historial de riesgo de fuga. `ciclo_compra_dias` es el ciclo
    de compra individual del cliente (no un umbral fijo global) y `severidad`
    (ronda 1, feature 002) distingue `en_riesgo` de `inactivo` (FR-009, FR-010)."""

    __tablename__ = "churn_score"
    __table_args__ = (UniqueConstraint("household_id", "fecha_calculo"),)

    churn_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    household_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.household_id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    ciclo_compra_dias: Mapped[int | None] = mapped_column(Integer)
    severidad: Mapped[str | None] = mapped_column(String(20))
    fecha_calculo: Mapped[date] = mapped_column(Date, nullable=False)
