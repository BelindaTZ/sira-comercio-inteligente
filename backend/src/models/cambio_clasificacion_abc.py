from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class CambioClasificacionAbc(Base):
    """`cambio_clasificacion_abc` (feature 005) — bitácora de reclasificaciones ABC
    para que el Jefe de Operaciones revise qué productos cambiaron de categoría en
    la corrida mensual (FR-010). No es la tabla de clasificación en sí (esa vive en
    `productos.clasificacion_abc`, sin dimensión de tienda) — sólo el changelog."""

    __tablename__ = "cambio_clasificacion_abc"

    cambio_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    clasificacion_anterior: Mapped[str | None] = mapped_column(String(1))
    clasificacion_nueva: Mapped[str] = mapped_column(String(1), nullable=False)
    fecha_calculo: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
