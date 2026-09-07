from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

FUENTES_CAPTURA = ("manual", "open_prices", "sintetico")


class PrecioCompetencia(Base):
    """`precio_competencia` (feature 003) — precio de referencia de competencia,
    tres fuentes vía `fuente_captura` (manual / open_prices / sintetico, research.md §5).
    La desviación (FR-015/FR-016) usa siempre la fila de `fecha_captura` más reciente
    por producto, sin importar la fuente."""

    __tablename__ = "precio_competencia"

    precio_competencia_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("productos.product_id", ondelete="CASCADE"), nullable=False
    )
    competidor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("competidores.competidor_id")
    )
    tienda_id: Mapped[int | None] = mapped_column(Integer)
    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    fecha_captura: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    es_promocional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fuente_captura: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    registrado_por: Mapped[int | None] = mapped_column(Integer)
