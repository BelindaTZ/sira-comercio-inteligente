from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

TRASLADO_ESTADOS = ("solicitado", "en_transito", "recibido", "cancelado", "rechazado")


class TrasladoStock(Base):
    """`traslados_stock` (reservada desde 001, primer consumidor: feature 012).

    Ciclo lineal: `solicitado` → `en_transito` (aprobado + despachado en la misma
    operación, research.md Decisión 1) → `recibido`; o `rechazado` / `cancelado`.
    `en_transito` es el "despachado" del lenguaje de negocio. Cada transición deja
    responsable y fecha en columnas aditivas (research.md Decisión 2, FR-011)."""

    __tablename__ = "traslados_stock"

    traslado_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tienda_origen_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tienda_destino_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="solicitado")
    empleado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    resuelto_por: Mapped[int | None] = mapped_column(Integer)
    fecha_resolucion: Mapped[datetime | None] = mapped_column(DateTime)
    recibido_por: Mapped[int | None] = mapped_column(Integer)
    fecha_recepcion: Mapped[datetime | None] = mapped_column(DateTime)
    fecha_cancelacion: Mapped[datetime | None] = mapped_column(DateTime)
