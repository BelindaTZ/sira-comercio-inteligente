from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DashboardOperativoEstado(Base):
    """`dashboard_operativo_estado` (feature 009, FR-006/FR-007).

    NO almacena ningún KPI operativo — esos viven dentro de cada feature 001-007.
    Sólo registra, por tienda y por nombre de dashboard operativo, la fecha de su
    dato más reciente (`MAX(fecha_hora)` de la tabla fuente, leído de solo
    lectura — research.md Decisión 3) y si está `disponible` (más de un día de
    antigüedad → `false`, FR-007).
    """

    __tablename__ = "dashboard_operativo_estado"

    estado_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    publicacion_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("registro_publicacion_dashboard.publicacion_id", ondelete="CASCADE"),
        nullable=False,
    )
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    nombre_dashboard: Mapped[str] = mapped_column(String(60), nullable=False)
    fecha_ultima_actualizacion: Mapped[datetime | None] = mapped_column(DateTime)
    disponible: Mapped[bool] = mapped_column(Boolean, nullable=False)
