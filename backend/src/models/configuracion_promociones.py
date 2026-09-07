from __future__ import annotations

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

CLAVE_SOPORTE_MINIMO = "soporte_minimo_regla"
CLAVE_CONFIANZA_MINIMA = "confianza_minima_regla"
CLAVE_VIGENCIA_CUPON_AFINIDAD = "vigencia_cupon_afinidad_dias"
CLAVE_ROTACION_MINIMA_LIQUIDACION = "rotacion_minima_liquidacion_semanal"
CLAVE_DESCUENTO_LIQUIDACION = "descuento_liquidacion_pct"


class ConfiguracionPromociones(Base):
    """`configuracion_promociones` (feature 005) — umbrales de negocio configurables
    (mismo patrón clave/valor que `configuracion_pricing` de 003 y
    `configuracion_pronostico` de 004)."""

    __tablename__ = "configuracion_promociones"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(250))
