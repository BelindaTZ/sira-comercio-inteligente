from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class AperturaCaja(Base):
    """`apertura_caja` (feature 006, FR-001) — reservada en el esquema desde 001,
    poblada por esta feature. Delimita además el "turno" del reporte mensual
    (research.md Decisión 3): la apertura más reciente de la misma caja con
    `fecha_hora <= cierre.fecha_hora`."""

    __tablename__ = "apertura_caja"

    apertura_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    caja_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cajero_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fondo_inicial: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
