from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class AnulacionVenta(Base):
    """`anulaciones_venta` (FR-007) — 1:1 con `ventas` (una venta se anula una vez)."""

    __tablename__ = "anulaciones_venta"

    anulacion_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ventas.venta_id"), unique=True, nullable=False
    )
    empleado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
