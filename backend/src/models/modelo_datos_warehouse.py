from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

# Entidades canónicas del warehouse (data-model.md §Tabla nueva 1 / research.md Decisión 1).
ENTIDADES_MODELO = (
    "fact_venta",
    "dim_cliente",
    "dim_producto",
    "dim_tienda",
    "dim_caja",
    "dim_empleado",
)
TIPOS_ENTIDAD = ("fact", "dimension")


class ModeloDatosWarehouse(Base):
    """`modelo_datos_warehouse` (feature 010, FR-001).

    Catálogo del modelo de datos único del warehouse: una fila por entidad
    (`fact_venta` + dimensiones), su tabla de origen en PostgreSQL y si su carga
    está activa. El DAG `carga_diaria_warehouse` sólo genera un task por entidad
    con `activa = true` (research.md Decisión 1) — así una tabla operativa nueva
    queda fuera de la carga hasta que el Jefe de TI la incorpora aquí.
    """

    __tablename__ = "modelo_datos_warehouse"

    entidad_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_entidad: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    tabla_origen_postgres: Mapped[str] = mapped_column(String(60), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    definido_por: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_definicion: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
