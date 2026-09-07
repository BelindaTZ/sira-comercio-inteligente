from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Lote(Base):
    """`lotes` — `codigo_lote_proveedor` (FR-014) sumado por 001. El consumo
    FIFO/FEFO ordena por `fecha_vencimiento ASC NULLS LAST, cantidad_recibida ASC,
    lote_id ASC` (research.md #4)."""

    __tablename__ = "lotes"

    lote_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_recibida: Mapped[int] = mapped_column(Integer, nullable=False)
    # Saldo vivo por lote (ronda 7). Se inicializa = cantidad_recibida y baja con
    # cada salida FIFO/FEFO. `inventario.cantidad_disponible` es el agregado.
    cantidad_disponible: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)
    codigo_lote_proveedor: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
