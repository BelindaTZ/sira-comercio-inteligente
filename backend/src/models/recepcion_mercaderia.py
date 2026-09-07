from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class RecepcionMercaderia(Base):
    """`recepcion_mercaderia` — segundo elemento del 3-way match (orden +
    recepción + factura). Solo contra una orden `aprobada` (FR-014)."""

    __tablename__ = "recepcion_mercaderia"

    recepcion_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    orden_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ordenes_compra.orden_id"), nullable=False
    )
    lote_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("lotes.lote_id"))
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    empleado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
