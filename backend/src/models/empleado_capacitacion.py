from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class EmpleadoCapacitacion(Base):
    """`empleado_capacitacion` (tabla reservada desde 001, poblada por 011). Una
    fila por empleado alcanzado en el fan-out al programar la capacitación (FR-004);
    `fecha_completado IS NULL` = pendiente. La consulta de cumplimiento por tienda
    (FR-005) se restringe al `Encargado_Tienda` a su propia tienda vía
    `empleados.tienda_id`."""

    __tablename__ = "empleado_capacitacion"

    empleado_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    capacitacion_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha_completado: Mapped[date | None] = mapped_column(Date)
