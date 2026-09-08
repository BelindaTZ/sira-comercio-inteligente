from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class PlanSucesion(Base):
    """`plan_sucesion` (tabla reservada desde 001, poblada por 011 — FR-008). Un
    candidato interno asociado a un puesto crítico, con fecha. La señalización de
    puestos críticos sin ninguna fila aquí (FR-009) es una consulta, no una columna
    de estado (research.md Decisión 4)."""

    __tablename__ = "plan_sucesion"

    sucesion_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    puesto_id: Mapped[int] = mapped_column(Integer, nullable=False)
    empleado_candidato_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
