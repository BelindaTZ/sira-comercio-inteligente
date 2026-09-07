from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class LineaVentaRemovida(Base):
    """`lineas_venta_removidas` (FR-027) — auditoría anti-fraude con CHECK de
    doble persona: quien autoriza no puede ser el cajero."""

    __tablename__ = "lineas_venta_removidas"
    __table_args__ = (
        CheckConstraint("cajero_id <> autoriza_empleado_id", name="chk_lvr_doble_persona"),
    )

    remocion_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ventas.venta_id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    cajero_id: Mapped[int] = mapped_column(Integer, nullable=False)
    autoriza_empleado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(200))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
