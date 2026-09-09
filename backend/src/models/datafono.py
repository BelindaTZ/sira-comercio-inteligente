from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

DATAFONO_ESTADOS = ("activo", "requiere_actualizacion", "fuera_servicio")


class Datafono(Base):
    """`datafonos` (feature 006, FR-006/FR-007/FR-008) — reservada desde 001. El
    estado `requiere_actualizacion` (ya en el enum) se reutiliza como "no conforme"
    frente al estándar de seguridad vigente (research.md Decisión 4)."""

    __tablename__ = "datafonos"

    datafono_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    caja_id: Mapped[int] = mapped_column(Integer, nullable=False)
    modelo: Mapped[str | None] = mapped_column(String(60))
    version_firmware: Mapped[str | None] = mapped_column(String(30))
    fecha_ultima_actualizacion: Mapped[date | None] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="activo")
    # feature 013: constancia (texto libre) de por qué se sacó de servicio; se
    # limpia al restablecerlo.
    motivo_fuera_servicio: Mapped[str | None] = mapped_column(String(200))
