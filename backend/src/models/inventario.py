from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Inventario(Base):
    """`inventario` — stock disponible por (producto, tienda). PK compuesta.
    `cantidad_disponible >= 0` lo garantiza un CHECK en BD (evita sobreventa)."""

    __tablename__ = "inventario"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    tienda_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    cantidad_disponible: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cantidad_minima: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cantidad_maxima: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
