from __future__ import annotations

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

CLAVE_PRECISION_MINIMA = "precision_minima_aprobacion"
CLAVE_UMBRAL_DEGRADACION = "umbral_degradacion_semanal_pct"
CLAVE_HISTORIAL_MINIMO = "historial_minimo_semanas"


class ConfiguracionPronostico(Base):
    """`configuracion_pronostico` (feature 004) — umbrales de negocio configurables
    (mismo patrón clave/valor que `configuracion_pricing` de 003)."""

    __tablename__ = "configuracion_pronostico"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(250))
