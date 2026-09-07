from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

# 'exceso_stock' agregado en la ronda 9 (FR-038).
ALERTA_TIPOS = ("reposicion", "vencimiento", "exceso_stock")
ALERTA_ESTADOS = ("pendiente", "atendida")


class AlertaInventario(Base):
    """`alertas_inventario` (FR-016/FR-020/FR-021). Índice único parcial
    `(product_id, tienda_id, tipo) WHERE estado='pendiente'` impide duplicar una
    alerta activa."""

    __tablename__ = "alertas_inventario"
    __table_args__ = (
        CheckConstraint(
            "tipo <> 'vencimiento' OR lote_id IS NOT NULL",
            name="chk_alerta_vencimiento_lote",
        ),
    )

    alerta_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    lote_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("lotes.lote_id"))
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    fecha_generada: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_atendida: Mapped[datetime | None] = mapped_column(DateTime)
    empleado_atiende_id: Mapped[int | None] = mapped_column(Integer)
