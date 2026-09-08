from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class RegistroCalidadCarga(Base):
    """`registro_calidad_carga` (feature 010, FR-007).

    Un registro señalado por incumplir una regla mínima de calidad durante una
    corrida (referencia rota, campo obligatorio vacío). La fila señalada NO se
    insertó en ClickHouse para esa corrida; el resto del lote sí — señalar,
    nunca bloquear (research.md Decisión 4).
    """

    __tablename__ = "registro_calidad_carga"

    registro_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    corrida_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    descripcion_problema: Mapped[str] = mapped_column(String(300), nullable=False)
    identificador_registro: Mapped[str | None] = mapped_column(String(100))
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
