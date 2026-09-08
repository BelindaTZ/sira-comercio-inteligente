"""Router de `ti/dashboards` —
`specs/009-dashboards-multinivel/contracts/dashboards-multinivel.md` #2-#5.

RBAC (data-model.md §RBAC):
- dashboard táctico: `dashboard_kpi` `select` en el módulo pedido — cada `Jefe_*`
  sobre el suyo, `Gerente_General` sobre cualquiera (permiso sembrado en los 6
  módulos). El alcance fino lo revalida la capa de servicio (FR-005).
- verificación operativa: `TI` → `dashboard_operativo_estado` `select` (`Jefe_TI`).
- forzar publicación (FR-010): `TI` → `registro_publicacion_dashboard` `insert`
  (`Jefe_TI`); sólo se monta fuera de producción.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_session
from src.core.security import CurrentPrincipal, Principal, _has_permission, require_permission
from src.modules.direccion.schemas import DashboardConsolidadoOut, DashboardKpiOut
from src.modules.ti.dashboards.repository import TiDashboardsRepository
from src.modules.ti.dashboards.schemas import (
    DashboardOperativoEstadoOut,
    ForzarPublicacionOut,
    VerificacionOperativosOut,
)
from src.modules.ti.dashboards.service import TiDashboardsService
from src.shared.dashboards import MODULOS_TACTICOS

router = APIRouter(prefix="/ti/dashboards", tags=["ti-dashboards"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ve_operativos = require_permission("TI", "dashboard_operativo_estado", "select")


def _svc(session: SessionDep) -> TiDashboardsService:
    return TiDashboardsService(TiDashboardsRepository(session))


ServiceDep = Annotated[TiDashboardsService, Depends(_svc)]


async def _puede_ver_tactico(
    modulo_nombre: str, principal: CurrentPrincipal, db: SessionDep
) -> Principal:
    """RBAC de módulo dinámico: `dashboard_kpi` `select` sobre el módulo pedido."""
    if modulo_nombre not in MODULOS_TACTICOS:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"'{modulo_nombre}' no es un departamento con dashboard táctico",
        )
    if not await _has_permission(db, principal.role_id, modulo_nombre, "dashboard_kpi", "select"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"El rol no tiene permiso select sobre {modulo_nombre}.dashboard_kpi",
        )
    return principal


# ============================================================ US2: dashboard táctico
@router.get("/tactico/{modulo_nombre}", response_model=DashboardConsolidadoOut)
async def dashboard_tactico(
    modulo_nombre: str,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_puede_ver_tactico)],
) -> DashboardConsolidadoOut:
    data = await svc.dashboard_tactico(modulo_nombre, principal)
    return DashboardConsolidadoOut(
        publicacion_id=data["publicacion_id"],
        fecha_publicacion=data["fecha_publicacion"],
        kpis=[DashboardKpiOut.model_validate(k) for k in data["kpis"]],
    )


# ============================================================ US3: verificación operativa
@router.get("/operativos/verificacion", response_model=VerificacionOperativosOut)
async def verificacion_operativos(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve_operativos)]
) -> VerificacionOperativosOut:
    data = await svc.verificacion_operativos()
    return VerificacionOperativosOut(
        publicacion_id=data["publicacion_id"],
        fecha_verificacion=data["fecha_verificacion"],
        estado_por_tienda=[
            DashboardOperativoEstadoOut.model_validate(e) for e in data["estado_por_tienda"]
        ],
    )


@router.get("/operativos/alertas", response_model=VerificacionOperativosOut)
async def alertas_operativos(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve_operativos)]
) -> VerificacionOperativosOut:
    data = await svc.alertas_operativos()
    return VerificacionOperativosOut(
        publicacion_id=data["publicacion_id"],
        fecha_verificacion=data["fecha_verificacion"],
        estado_por_tienda=[
            DashboardOperativoEstadoOut.model_validate(e) for e in data["estado_por_tienda"]
        ],
    )


# ============================================================ FR-010: forzar publicación (dev only)
if settings.app_env != "production":
    _fuerza = require_permission("TI", "registro_publicacion_dashboard", "insert")

    class ForzarPublicacionIn(BaseModel):
        modulo_nombre: str | None = None

    @router.post(
        "/{tipo}/forzar-publicacion",
        status_code=status.HTTP_202_ACCEPTED,
        response_model=ForzarPublicacionOut,
    )
    async def forzar_publicacion(
        tipo: Literal["estrategico", "tactico", "operativo"],
        session: SessionDep,
        _: Annotated[Principal, Depends(_fuerza)],
        data: ForzarPublicacionIn | None = None,
    ) -> ForzarPublicacionOut:
        from src.modules.direccion.jobs import publicar_dashboard_estrategico
        from src.modules.ti.dashboards.jobs import (
            publicar_dashboards_tacticos,
            verificar_dashboards_operativos,
        )

        if tipo == "estrategico":
            res = await publicar_dashboard_estrategico.ejecutar(session)
        elif tipo == "operativo":
            res = await verificar_dashboards_operativos.ejecutar(session)
        else:
            modulos = [data.modulo_nombre] if data is not None and data.modulo_nombre else None
            res = await publicar_dashboards_tacticos.ejecutar(session, modulos=modulos)

        pub_id = res.get("publicacion_id")
        if pub_id is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "No se pudo generar la publicación (sin datos fuente o módulo inválido)",
            )
        return ForzarPublicacionOut(publicacion_id=pub_id, estado="en_proceso")
