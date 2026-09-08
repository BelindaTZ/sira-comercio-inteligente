from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class AccionRetencion(Base):
    """`acciones_retencion` (feature 011, FR-002) — única tabla nueva de la feature
    (research.md Decisión 1). Registra una acción aplicada a un empleado, con fecha
    y descripción, consultable en cualquier momento. Se permite para un empleado en
    un puesto no crítico (Edge Case); sólo los puestos críticos alimentan el KPI de
    OT-8.1."""

    __tablename__ = "acciones_retencion"

    accion_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empleado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
