from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Empleado(Base):
    """`empleados` (desde 001, referenciada por FK; feature 008 la registra como
    entidad propia). Al pasar `activo` a `false` dispara el trigger
    `trg_inhabilitar_cuenta_baja_empleado` (research.md Decisión 4)."""

    __tablename__ = "empleados"

    empleado_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tienda_id: Mapped[int | None] = mapped_column(Integer)
    puesto_id: Mapped[int] = mapped_column(Integer, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(150))
    telefono: Mapped[str | None] = mapped_column(String(20))
    fecha_contratacion: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_baja: Mapped[date | None] = mapped_column(Date)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
