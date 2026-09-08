from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class UmbralMermaCategoria(Base):
    """`umbral_merma_categoria` (feature 006, FR-017) — una fila por categoría,
    actualizable in place (research.md Decisión 8: sin valor de auditoría en las
    versiones pasadas, a diferencia del estándar de seguridad y el protocolo)."""

    __tablename__ = "umbral_merma_categoria"

    product_category: Mapped[str] = mapped_column(String(100), primary_key=True)
    porcentaje_umbral: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    definido_por: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
