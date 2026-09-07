from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

ESTADOS_CANDIDATO = ("candidato", "ejecutado")


class CandidatoLiquidacion(Base):
    """`candidato_liquidacion` (feature 005, FR-012/FR-014) — producto categoría C
    con rotación local bajo el umbral, propuesto para liquidación en una tienda y
    semana. Si el Encargado no lo ejecuta, la siguiente corrida genera una fila
    nueva (no hay estado `descartado`)."""

    __tablename__ = "candidato_liquidacion"
    __table_args__ = (UniqueConstraint("product_id", "tienda_id", "semana", "anio"),)

    candidato_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("productos.product_id", ondelete="CASCADE"), nullable=False
    )
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    semana: Mapped[int] = mapped_column(Integer, nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    rotacion_reciente_calculada: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    descuento_sugerido_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="candidato")
    fecha_ejecucion: Mapped[datetime | None] = mapped_column(DateTime)
    ejecutado_por: Mapped[int | None] = mapped_column(Integer)
