from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class PoliticaSeguridadPagos(Base):
    """`politica_seguridad_pagos` (feature 007, FR-012 a FR-014) — texto de
    referencia versionado, append-only (research.md Decisión 5, mismo criterio que
    `protocolo_escalamiento` de 006). Vigente = fila más reciente por
    `fecha_creacion`; las versiones anteriores siguen consultables por `politica_id`
    para saber cuál regía cuando se abrió un incidente en curso (FR-014)."""

    __tablename__ = "politica_seguridad_pagos"

    politica_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    definido_por: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
