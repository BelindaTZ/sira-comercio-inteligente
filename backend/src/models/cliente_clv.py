from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ClienteClv(Base):
    """`cliente_clv` — historial de CLV (un registro por `fecha_calculo`, nunca se
    sobrescribe — Principio II). El job semanal inserta una fila nueva (FR-005)."""

    __tablename__ = "cliente_clv"
    __table_args__ = (UniqueConstraint("household_id", "fecha_calculo"),)

    clv_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    household_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.household_id", ondelete="CASCADE"), nullable=False
    )
    nivel_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("niveles_fidelizacion.nivel_id")
    )
    clv_score: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    fecha_calculo: Mapped[date] = mapped_column(Date, nullable=False)
