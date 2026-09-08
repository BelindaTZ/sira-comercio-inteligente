from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

INCIDENTE_ESTADOS = ("abierto", "en_revision", "cerrado")
INCIDENTE_RESULTADOS = ("fraude_confirmado", "descartado")


class IncidenteFraude(Base):
    """`incidentes_fraude` (feature 006) — reservada desde 001 y extendida
    aditivamente (data-model.md, research.md Decisión 6): `cierre_id` pasa a
    nullable; se agregan `ajuste_id`, `acciones_tomadas`, `resultado`,
    `actualizado_por`, `fecha_actualizacion`. Un incidente puede originarse en un
    patrón de cuadre (US3), en un ajuste de inventario anómalo (FR-010) o
    registrarse directamente (US4). Sigue su curso aunque el empleado tenga
    `fecha_baja` (FR-016)."""

    __tablename__ = "incidentes_fraude"

    incidente_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cierre_id: Mapped[int | None] = mapped_column(BigInteger)
    ajuste_id: Mapped[int | None] = mapped_column(BigInteger)
    empleado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    acciones_tomadas: Mapped[str | None] = mapped_column(Text)
    resultado: Mapped[str | None] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="abierto")
    actualizado_por: Mapped[int | None] = mapped_column(Integer)
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(DateTime)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
