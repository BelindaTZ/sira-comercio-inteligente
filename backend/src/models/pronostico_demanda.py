from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class PronosticoDemanda(Base):
    """`pronostico_demanda` (feature 004) — una predicción por
    modelo/producto/tienda/semana (research.md Decisión 1). El pronóstico
    "vigente" es el que pertenece al `modelo_demanda` con `estado = 'aprobado'`.
    """

    __tablename__ = "pronostico_demanda"
    __table_args__ = (UniqueConstraint("modelo_id", "product_id", "tienda_id", "semana", "anio"),)

    pronostico_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    modelo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("modelo_demanda.modelo_id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    semana: Mapped[int] = mapped_column(Integer, nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_pronosticada: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
