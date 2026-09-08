from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Capacitacion(Base):
    """`capacitaciones` (tabla reservada desde 001, poblada por 011 — FR-003). Los
    roles objetivo NO se persisten aquí (research.md Decisión 2): se resuelven sólo
    al programarla, para el fan-out inmediato hacia `empleado_capacitacion`."""

    __tablename__ = "capacitaciones"

    capacitacion_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
