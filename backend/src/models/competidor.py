from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

TIPOS_COMPETIDOR = ("supermercado", "tienda_barrio", "tienda_digital")


class Competidor(Base):
    """`competidores` (feature 003, FR-014) — catálogo de competidores nombrados
    para la captura manual de precio de referencia. Sin relación con las tiendas
    propias de Marzú."""

    __tablename__ = "competidores"

    competidor_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    ciudad: Mapped[str | None] = mapped_column(String(100))
