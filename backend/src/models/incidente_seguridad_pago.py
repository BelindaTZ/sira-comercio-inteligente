from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

INCIDENTE_SEGURIDAD_ESTADOS = ("abierto", "en_investigacion", "cerrado")


class IncidenteSeguridadPago(Base):
    """`incidente_seguridad_pago` (feature 007, FR-008 a FR-011) — entidad nueva,
    independiente de `incidentes_fraude` (006, research.md Decisión 4): no exige un
    empleado implicado (`datafono_id` es opcional; `registrado_por` es quién lo
    reporta, no un sospechoso). Un mismo `datafono_id` puede tener a la vez un
    incidente de fraude y uno de seguridad de pago sin relación entre sí (FR-010)."""

    __tablename__ = "incidente_seguridad_pago"

    incidente_seguridad_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    datafono_id: Mapped[int | None] = mapped_column(Integer)
    registrado_por: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="abierto")
    actualizado_por: Mapped[int | None] = mapped_column(Integer)
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(DateTime)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
