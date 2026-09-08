from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class RolPuesto(Base):
    """`roles_puesto` (desde 001; feature 011 la extiende con `es_critico`). El
    puesto crítico (FR-001) alimenta la retención (OT-8.1) y el plan de sucesión
    (OT-8.4). Marca aditiva: las filas de 001 quedan en `false` por defecto."""

    __tablename__ = "roles_puesto"

    puesto_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(200))
    es_critico: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
