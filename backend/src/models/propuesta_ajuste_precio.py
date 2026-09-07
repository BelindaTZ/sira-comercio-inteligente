from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

ESTADOS_PROPUESTA = ("pendiente", "aprobada", "rechazada")


class PropuestaAjustePrecio(Base):
    """`propuesta_ajuste_precio` (feature 003) — propuesta generada por el job
    semanal, nunca publicada sin aprobación explícita de Jefe_Comercial (SC-002).
    Al aprobarse actualiza `productos.precio_base` + `historial_precios` (research.md §1).
    """

    __tablename__ = "propuesta_ajuste_precio"

    propuesta_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("productos.product_id", ondelete="CASCADE"), nullable=False
    )
    precio_actual: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    precio_propuesto: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    margen_esperado_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    fecha_generada: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_resolucion: Mapped[datetime | None] = mapped_column(DateTime)
    aprobado_por: Mapped[int | None] = mapped_column(Integer)
