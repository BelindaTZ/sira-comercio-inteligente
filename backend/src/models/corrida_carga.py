from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

TIPOS_CARGA = ("completa", "incremental")
ORIGENES_CARGA = ("postgres", "minio_landing_zone")
ESTADOS_CORRIDA = ("en_progreso", "exitosa", "fallida")


class CorridaCarga(Base):
    """`corrida_carga` (feature 010, FR-002 a FR-006, FR-012).

    Una fila por corrida de carga de UNA entidad del modelo (no del DAG completo,
    research.md Decisión 2). El estado de cada corrida es un registro real
    (Principio II) — nunca se reporta desde los logs de Airflow (SC-004).

    Exclusión mutua por destino (FR-005): índice único parcial
    `uq_corrida_carga_en_progreso ON (entidad_id) WHERE estado = 'en_progreso'`.
    `duracion_segundos` se deriva en la capa de lectura (`fecha_fin - fecha_inicio`).
    """

    __tablename__ = "corrida_carga"

    corrida_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    entidad_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_carga: Mapped[str] = mapped_column(String(12), nullable=False)
    origen: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(12), nullable=False, default="en_progreso"
    )
    filas_cargadas: Mapped[int | None] = mapped_column(Integer)
    filas_error: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime)
