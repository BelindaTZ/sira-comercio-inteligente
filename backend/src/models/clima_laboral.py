from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ClimaLaboral(Base):
    """`clima_laboral` (tabla reservada desde 001, poblada por 011 — FR-006). Un
    resultado promedio por tienda y periodo semestral (`'AAAA-Sn'`). Un periodo sin
    fila = sin dato, nunca inventado (FR-010). El cruce con la tasa de rotación del
    mismo periodo (FR-007) se calcula on-the-fly desde `empleados.fecha_baja`
    (research.md Decisión 3), no se persiste aquí."""

    __tablename__ = "clima_laboral"

    encuesta_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tienda_id: Mapped[int | None] = mapped_column(Integer)
    periodo: Mapped[str] = mapped_column(String(10), nullable=False)
    resultado_promedio: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    fecha: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
