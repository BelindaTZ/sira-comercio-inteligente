from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

TIPOS_DASHBOARD = ("estrategico", "tactico", "operativo")


class RegistroPublicacionDashboard(Base):
    """`registro_publicacion_dashboard` (feature 009, FR-001/FR-004/FR-006/FR-008).

    Una fila por corrida del job diario (o del trigger manual de FR-010) para
    cualquiera de los tres niveles, éxito o falla. Es el registro real que
    respalda la fecha de "última actualización" mostrada al usuario (Principio II)
    — nunca se dice "actualizado ahora" sin una fila que lo pruebe.

    `modulo_id` sólo aplica cuando `tipo_dashboard = 'tactico'` (una publicación
    por cada uno de los 6 módulos con Jefe propio, research.md Decisión 4).
    """

    __tablename__ = "registro_publicacion_dashboard"

    publicacion_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tipo_dashboard: Mapped[str] = mapped_column(String(20), nullable=False)
    modulo_id: Mapped[int | None] = mapped_column(Integer)
    exito: Mapped[bool] = mapped_column(nullable=False)
    detalle_error: Mapped[str | None] = mapped_column(String)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
