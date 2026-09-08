"""Router del módulo Direccion —
`specs/009-dashboards-multinivel/contracts/dashboards-multinivel.md` #1.

RBAC: módulo `Direccion` (primer consumidor real), rol `Gerente_General` con
lectura global ya existente. Sin lógica de negocio (Principio XI).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.security import Principal, require_permission
from src.modules.direccion.repository import DireccionRepository
from src.modules.direccion.schemas import DashboardConsolidadoOut, DashboardKpiOut
from src.modules.direccion.service import DireccionService

router = APIRouter(prefix="/direccion", tags=["direccion"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ve = require_permission("Direccion", "dashboard_kpi", "select")


def _svc(session: SessionDep) -> DireccionService:
    return DireccionService(DireccionRepository(session))


ServiceDep = Annotated[DireccionService, Depends(_svc)]


@router.get("/dashboard-estrategico", response_model=DashboardConsolidadoOut)
async def dashboard_estrategico(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve)]
) -> DashboardConsolidadoOut:
    data = await svc.dashboard_estrategico()
    return DashboardConsolidadoOut(
        publicacion_id=data["publicacion_id"],
        fecha_publicacion=data["fecha_publicacion"],
        kpis=[DashboardKpiOut.model_validate(k) for k in data["kpis"]],
    )
