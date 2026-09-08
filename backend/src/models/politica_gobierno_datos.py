from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class PoliticaGobiernoDatos(Base):
    """`politica_gobierno_datos` (feature 010, FR-009, FR-010).

    Documento de referencia versionado (calidad, trazabilidad, acceso).
    Append-only: cada actualización inserta una fila nueva, nunca se hace
    UPDATE/DELETE; la vigente es la de `fecha_creacion` más reciente — mismo
    patrón que `protocolo_escalamiento_incidentes` (006) y
    `politica_seguridad_pagos` (007), research.md Decisión 5.
    """

    __tablename__ = "politica_gobierno_datos"

    politica_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    definido_por: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
