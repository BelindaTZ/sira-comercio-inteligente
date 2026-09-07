from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class StockMaximoCategoria(Base):
    """`stock_maximo_categoria` (FR-037, Ronda 9) — valor vigente por categoría y
    tienda; único `(product_category, tienda_id)`, una redefinición hace UPDATE.

    Las FK a `tiendas`/`empleados` (feature 008) viven sólo en la BD; aquí se
    mapean como `Integer` para no acoplar el ORM a modelos de otra feature.
    """

    __tablename__ = "stock_maximo_categoria"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_category: Mapped[str] = mapped_column(String(100), nullable=False)
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_maxima: Mapped[int] = mapped_column(Integer, nullable=False)
    empleado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_definicion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
