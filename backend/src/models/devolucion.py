from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Devolucion(Base):
    """`devoluciones` — `reintegra_inventario` (FR-025) lo decide el motivo."""

    __tablename__ = "devoluciones"

    devolucion_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ventas.venta_id"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[str] = mapped_column(String(200), nullable=False)
    empleado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reintegra_inventario: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
