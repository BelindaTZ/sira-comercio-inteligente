from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class EventoQuiebreStock(Base):
    """`eventos_quiebre_stock` (FR-022) — registro append-only, no se edita ni
    anula; alimenta el reporte mensual de demanda perdida (OO-5.2.2)."""

    __tablename__ = "eventos_quiebre_stock"

    evento_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    empleado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    demanda_estimada_no_satisfecha: Mapped[int | None] = mapped_column(Integer)
    # Ronda 10 (FR-043): se fija al insertar según productos.clasificacion_abc='A'.
    es_alta_demanda: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
