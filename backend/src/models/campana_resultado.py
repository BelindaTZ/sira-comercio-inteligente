from __future__ import annotations

from datetime import date

from sqlalchemy import Computed, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

DECISION_CAMPANA = ("aprobada_escalar", "descartada")


class CampanaResultado(Base):
    """`campana_resultado` (ronda 2, feature 002) — cierre de una campaña de
    reactivación: `uplift` es columna generada en BD (`tasa_tratado - tasa_control`),
    nunca calculada en la app (FR-017/FR-018)."""

    __tablename__ = "campana_resultado"

    campaign_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("campanas.campaign_id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
    )
    tasa_retorno_tratado: Mapped[float | None] = mapped_column(Numeric(5, 4))
    tasa_retorno_control: Mapped[float | None] = mapped_column(Numeric(5, 4))
    uplift: Mapped[float | None] = mapped_column(
        Numeric(5, 4),
        Computed("tasa_retorno_tratado - tasa_retorno_control", persisted=True),
    )
    decision: Mapped[str | None] = mapped_column(String(20))
    empleado_decide_id: Mapped[int | None] = mapped_column(Integer)
    fecha_calculo: Mapped[date | None] = mapped_column(Date)
