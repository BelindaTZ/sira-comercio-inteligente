from __future__ import annotations

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class MargenObjetivo(Base):
    """`margenes_objetivo` — margen objetivo (%) por categoría + regla de ajuste.

    Existe en el esquema base sin usar hasta la feature 003; `factor_sensibilidad`
    (nullable) la activa como regla de ajuste de precio: `NULL` = la categoría aún
    no tiene regla activa y el job semanal la omite (research.md §2).
    """

    __tablename__ = "margenes_objetivo"

    product_category: Mapped[str] = mapped_column(String(100), primary_key=True)
    margen_objetivo_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    factor_sensibilidad: Mapped[float | None] = mapped_column(Numeric(4, 2))
