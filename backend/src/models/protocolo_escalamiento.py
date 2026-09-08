from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ProtocoloEscalamiento(Base):
    """`protocolo_escalamiento` (feature 006, FR-012/FR-013) — texto de referencia
    versionado, append-only (research.md Decisión 7): el protocolo vigente es la
    fila más reciente por `fecha_creacion`. No es un motor de flujo (spec.md
    Assumptions)."""

    __tablename__ = "protocolo_escalamiento"

    protocolo_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    definido_por: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
