from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class UbicacionProducto(Base):
    """`ubicacion_producto` — dónde está el SKU en sala, una fila por
    (producto, tienda). La mantiene el Reponedor/Encargado (migración 0021)."""

    __tablename__ = "ubicacion_producto"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    tienda_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    pasillo: Mapped[str] = mapped_column(String(40), nullable=False)
    gondola: Mapped[str | None] = mapped_column(String(20))
    nivel: Mapped[str | None] = mapped_column(String(20))
    actualizado_por: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
