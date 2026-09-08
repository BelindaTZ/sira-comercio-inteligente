from __future__ import annotations

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

# Umbral (en unidades, valor absoluto) a partir del cual un ajuste de inventario
# de 001 con diferencia negativa se señala en el reporte mensual (FR-010).
CLAVE_UMBRAL_AJUSTE_ANOMALO = "umbral_ajuste_inventario_anomalo"


class ConfiguracionCaja(Base):
    """`configuracion_caja` (feature 006) — umbrales de negocio configurables,
    mismo patrón clave/valor que `configuracion_pricing` (003),
    `configuracion_pronostico` (004) y `configuracion_promociones` (005). Hoy solo
    aloja el umbral de ajuste de inventario anómalo del reporte de patrones
    (FR-010, "umbral configurable")."""

    __tablename__ = "configuracion_caja"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(250))
