from __future__ import annotations

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

CLAVE_MARGEN_MINIMO_GLOBAL = "margen_minimo_global_pct"
CLAVE_TOLERANCIA_AJUSTE = "tolerancia_ajuste_pp"
CLAVE_UMBRAL_COMPETENCIA = "umbral_alerta_competencia_pct"


class ConfiguracionPricing(Base):
    """`configuracion_pricing` (feature 003) — clave/valor para los 3 números que
    el spec pide configurables: margen mínimo global de respaldo, tolerancia de
    desviación para generar propuestas y umbral de alerta de competencia."""

    __tablename__ = "configuracion_pricing"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(250))
