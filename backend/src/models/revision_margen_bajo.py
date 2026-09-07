from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class RevisionMargenBajo(Base):
    """`revision_margen_bajo` (feature 003, FR-012) — acción correctiva registrada
    sobre una línea marcada `margen_bajo_minimo`. 1:1 con la línea (corregir la
    nota es un UPDATE, nunca una fila nueva)."""

    __tablename__ = "revision_margen_bajo"

    revision_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_detalle_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("venta_detalle.venta_detalle_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    revisado_por: Mapped[int] = mapped_column(Integer, nullable=False)
    accion_correctiva: Mapped[str] = mapped_column(String(500), nullable=False)
    fecha_revision: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
