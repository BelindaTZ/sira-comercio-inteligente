from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ConfiguracionSeguridadPagos(Base):
    """`configuracion_seguridad_pagos` (feature 006, FR-007) — estándar mínimo de
    firmware de datáfono, append-only (research.md Decisión 5): cada cambio inserta
    una fila; el estándar vigente es la de `vigente_desde` más reciente. El
    historial tiene valor de auditoría de seguridad de pagos."""

    __tablename__ = "configuracion_seguridad_pagos"

    config_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version_minima_firmware: Mapped[str] = mapped_column(String(30), nullable=False)
    vigente_desde: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    actualizado_por: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
