from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class MedioPago(Base):
    """`medios_pago` — catálogo de 001, extendido aditivamente por 007 (FR-005 a
    FR-007): `aprobado`/`aprobado_por`/`fecha_aprobacion` dejan constancia del alta;
    `fecha_baja` marca la baja sin borrar la fila ni desasociar ninguna venta ya
    registrada. Sólo `aprobado=true AND fecha_baja IS NULL` se ofrece en caja."""

    __tablename__ = "medios_pago"

    medio_pago_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    aprobado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    aprobado_por: Mapped[int | None] = mapped_column(Integer)
    fecha_aprobacion: Mapped[datetime | None] = mapped_column(DateTime)
    fecha_baja: Mapped[datetime | None] = mapped_column(DateTime)
