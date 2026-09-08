"""DireccionRepository — acceso a datos del snapshot publicado del dashboard
estratégico (feature 009). Sin lógica de negocio (Principio XI).

Sólo lee `registro_publicacion_dashboard` / `dashboard_kpi` de PostgreSQL — nunca
consulta ClickHouse (Principio III). El job de publicación escribe a través de
este mismo repositorio.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.dashboard_kpi import DashboardKpi
from src.models.registro_publicacion_dashboard import RegistroPublicacionDashboard


class DireccionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def flush(self) -> None:
        await self.session.flush()

    async def ultima_publicacion_exitosa(self) -> RegistroPublicacionDashboard | None:
        """FR-003 — el dashboard estratégico siempre devuelve la publicación
        exitosa más reciente."""
        stmt = (
            select(RegistroPublicacionDashboard)
            .where(
                RegistroPublicacionDashboard.tipo_dashboard == "estrategico",
                RegistroPublicacionDashboard.exito.is_(True),
            )
            .order_by(
                RegistroPublicacionDashboard.fecha_hora.desc(),
                RegistroPublicacionDashboard.publicacion_id.desc(),
            )
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def kpis_de(self, publicacion_id: int) -> list[DashboardKpi]:
        stmt = (
            select(DashboardKpi)
            .where(DashboardKpi.publicacion_id == publicacion_id)
            .order_by(DashboardKpi.dimension, DashboardKpi.kpi_id)
        )
        return list((await self.session.scalars(stmt)).all())

    # ------------------------------------------------------------ escritura (job diario)
    async def registrar_publicacion(
        self, *, exito: bool, detalle_error: str | None = None
    ) -> RegistroPublicacionDashboard:
        fila = RegistroPublicacionDashboard(
            tipo_dashboard="estrategico", exito=exito, detalle_error=detalle_error
        )
        self.session.add(fila)
        await self.session.flush()
        await self.session.refresh(fila)
        return fila

    async def agregar_kpi(
        self,
        *,
        publicacion_id: int,
        dimension: str,
        nombre_kpi: str,
        valor,
        disponible: bool,
    ) -> None:
        self.session.add(
            DashboardKpi(
                publicacion_id=publicacion_id,
                dimension=dimension,
                nombre_kpi=nombre_kpi,
                valor=valor,
                disponible=disponible,
            )
        )
