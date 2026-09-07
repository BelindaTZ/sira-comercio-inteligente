from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class HistorialPrecio(Base):
    """`historial_precios` — vigencias de precio por producto (FR-006).

    Existe en el esquema base sin usar hasta la feature 003. La feature escribe
    siempre con `tienda_id = NULL` (precio único de cadena en el MVP, research.md §1);
    `fecha_fin IS NULL` = vigente.
    """

    __tablename__ = "historial_precios"

    historial_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("productos.product_id", ondelete="CASCADE"), nullable=False
    )
    tienda_id: Mapped[int | None] = mapped_column(Integer)
    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date | None] = mapped_column(Date)
