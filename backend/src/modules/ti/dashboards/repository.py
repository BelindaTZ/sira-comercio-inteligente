"""Repositorio de `ti/dashboards` — acceso a datos de los snapshots táctico y
operativo (feature 009). Sin lógica de negocio (Principio XI). Nunca consulta
ClickHouse (Principio III).
"""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.dashboard_kpi import DashboardKpi
from src.models.dashboard_operativo_estado import DashboardOperativoEstado
from src.models.registro_publicacion_dashboard import RegistroPublicacionDashboard


class TiDashboardsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def flush(self) -> None:
        await self.session.flush()

    # ------------------------------------------------------------ táctico (US2)
    async def modulo_id_por_nombre(self, nombre: str) -> int | None:
        return await self.session.scalar(
            text("SELECT modulo_id FROM modulos WHERE nombre = :n"), {"n": nombre}
        )

    async def ultima_publicacion_tactica(
        self, modulo_id: int
    ) -> RegistroPublicacionDashboard | None:
        stmt = (
            select(RegistroPublicacionDashboard)
            .where(
                RegistroPublicacionDashboard.tipo_dashboard == "tactico",
                RegistroPublicacionDashboard.modulo_id == modulo_id,
                RegistroPublicacionDashboard.exito.is_(True),
            )
            .order_by(
                RegistroPublicacionDashboard.fecha_hora.desc(),
                RegistroPublicacionDashboard.publicacion_id.desc(),
            )
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def ultima_publicacion_operativa(self) -> RegistroPublicacionDashboard | None:
        stmt = (
            select(RegistroPublicacionDashboard)
            .where(
                RegistroPublicacionDashboard.tipo_dashboard == "operativo",
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

    # ------------------------------------------------------------ operativo (US3)
    async def estado_operativo(
        self, publicacion_id: int, *, solo_no_disponibles: bool = False
    ) -> list[DashboardOperativoEstado]:
        stmt = select(DashboardOperativoEstado).where(
            DashboardOperativoEstado.publicacion_id == publicacion_id
        )
        if solo_no_disponibles:
            stmt = stmt.where(DashboardOperativoEstado.disponible.is_(False))
        stmt = stmt.order_by(
            DashboardOperativoEstado.tienda_id,
            DashboardOperativoEstado.nombre_dashboard,
        )
        return list((await self.session.scalars(stmt)).all())

    # ------------------------------------------------------------ escritura (jobs)
    async def registrar_publicacion(
        self,
        *,
        tipo_dashboard: str,
        modulo_id: int | None = None,
        exito: bool,
        detalle_error: str | None = None,
    ) -> RegistroPublicacionDashboard:
        fila = RegistroPublicacionDashboard(
            tipo_dashboard=tipo_dashboard,
            modulo_id=modulo_id,
            exito=exito,
            detalle_error=detalle_error,
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

    async def agregar_estado_operativo(
        self,
        *,
        publicacion_id: int,
        tienda_id: int,
        nombre_dashboard: str,
        fecha_ultima_actualizacion,
        disponible: bool,
    ) -> None:
        self.session.add(
            DashboardOperativoEstado(
                publicacion_id=publicacion_id,
                tienda_id=tienda_id,
                nombre_dashboard=nombre_dashboard,
                fecha_ultima_actualizacion=fecha_ultima_actualizacion,
                disponible=disponible,
            )
        )
