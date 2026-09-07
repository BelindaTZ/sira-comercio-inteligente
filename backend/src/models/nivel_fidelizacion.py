from __future__ import annotations

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class NivelFidelizacion(Base):
    """`niveles_fidelizacion` — umbral de CLV mínimo por nivel; la reclasificación
    automática asigna el nivel más alto cuyo `umbral_clv_min` no supera el CLV (FR-007)."""

    __tablename__ = "niveles_fidelizacion"

    nivel_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    umbral_clv_min: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
