from __future__ import annotations

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ConfiguracionInventario(Base):
    """`configuracion_inventario` (Ronda 9) — parámetros clave/valor del negocio
    para el punto de reposición y las alertas de vencimiento (FR-016, FR-020).
    Mismo patrón que `configuracion_pricing` (feature 003)."""

    __tablename__ = "configuracion_inventario"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(250))
