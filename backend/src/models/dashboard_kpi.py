from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DashboardKpi(Base):
    """`dashboard_kpi` (feature 009, FR-001/FR-002/FR-004).

    Snapshot de un valor ya calculado por otra feature (Principio VIII — esta
    feature no recalcula KPIs). Sirve al dashboard estratégico (`dimension` =
    código de Objetivo Estratégico `'OE-1'`..`'OE-8'`) y a los tácticos
    (`dimension` = `modulos.nombre`), diferenciados por `publicacion_id`
    (research.md Decisión 2).

    `disponible = false` es el mecanismo explícito para un KPI sin fuente real
    (OE-4 Market Share/NPS) o con datos insuficientes — `valor` queda `NULL`,
    nunca inventado (Principio VII).
    """

    __tablename__ = "dashboard_kpi"

    kpi_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    publicacion_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("registro_publicacion_dashboard.publicacion_id", ondelete="CASCADE"),
        nullable=False,
    )
    dimension: Mapped[str] = mapped_column(String(60), nullable=False)
    nombre_kpi: Mapped[str] = mapped_column(String(100), nullable=False)
    valor: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    disponible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
