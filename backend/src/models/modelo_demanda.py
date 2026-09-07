from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

ESTADOS_MODELO = ("pendiente", "aprobado", "rechazado", "reemplazado")


class ModeloDemanda(Base):
    """`modelo_demanda` (feature 004) — una versión de modelo de pronóstico.

    Mismo patrón de aprobación pendiente/aprobado/rechazado que
    `propuesta_ajuste_precio` de 003 (research.md Decisión 7). Sólo puede haber
    un modelo `aprobado` a la vez (índice único parcial en la BD).
    """

    __tablename__ = "modelo_demanda"

    modelo_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    fecha_entrenamiento: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    metrica_precision_validacion: Mapped[float | None] = mapped_column(Numeric(6, 4))
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    fecha_resolucion: Mapped[datetime | None] = mapped_column(DateTime)
    aprobado_por: Mapped[int | None] = mapped_column(Integer)
    observaciones: Mapped[str | None] = mapped_column(String(500))
