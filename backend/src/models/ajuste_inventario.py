from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Computed, Date, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class AjusteInventario(Base):
    """`ajustes_inventario` (FR-017) — `diferencia` es columna generada en BD
    (`GENERATED ALWAYS AS`), dato derivado puro, nunca calculado en la app."""

    __tablename__ = "ajustes_inventario"

    ajuste_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_sistema: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_fisica: Mapped[int] = mapped_column(Integer, nullable=False)
    diferencia: Mapped[int] = mapped_column(
        Integer, Computed("cantidad_fisica - cantidad_sistema", persisted=True)
    )
    empleado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
