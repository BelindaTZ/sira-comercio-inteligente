from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

FRECUENCIA_REPOSICION = ("semanal", "mensual", "trimestral")


class Proveedor(Base):
    """`proveedores` — con `frecuencia_reposicion` (FR-028) y `ruc` (FR-032) de 001."""

    __tablename__ = "proveedores"

    proveedor_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    contacto: Mapped[str | None] = mapped_column(String(150))
    telefono: Mapped[str | None] = mapped_column(String(20))
    condiciones_pago: Mapped[str | None] = mapped_column(String(100))
    frecuencia_reposicion: Mapped[str | None] = mapped_column(String(20))
    ruc: Mapped[str | None] = mapped_column(String(13))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
