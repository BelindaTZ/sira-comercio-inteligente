from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Computed, DateTime, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class CierreCaja(Base):
    """`cierre_caja` (feature 006, FR-002/FR-003/FR-004) — `diferencia` es columna
    generada en BD (`GENERATED ALWAYS AS`), dato derivado puro nunca calculado en
    la app (Principio V). `total_esperado` se calcula server-side antes del INSERT
    (research.md Decisión 1), nunca se acepta del cliente."""

    __tablename__ = "cierre_caja"

    cierre_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    caja_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cajero_id: Mapped[int] = mapped_column(Integer, nullable=False)
    total_esperado: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total_registrado: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    diferencia: Mapped[float] = mapped_column(
        Numeric(10, 2), Computed("total_registrado - total_esperado", persisted=True)
    )
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
