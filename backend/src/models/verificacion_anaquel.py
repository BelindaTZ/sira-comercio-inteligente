from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class VerificacionAnaquel(Base):
    """`verificacion_anaquel` (FR-042, Ronda 10) — verificación diaria de anaquel
    de un producto clasificación A. Único `(product_id, tienda_id, fecha)`: un
    segundo registro del mismo día actualiza la fila (upsert).

    Las FK viven en la BD; aquí columnas `Integer` (mismo criterio que el resto
    de modelos de esta feature para referencias cruzadas).
    """

    __tablename__ = "verificacion_anaquel"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    disponible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    empleado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
