"""Router del módulo RRHH — `contracts/auth-administracion-sistema.md`.

RBAC: módulo `RRHH` para `Jefe_RRHH` (primer uso del módulo). Sólo el CRUD base de
empleado; su ampliación es de 011-recursos-humanos.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.security import Principal, require_permission
from src.modules.rrhh.repository import RRHHRepository
from src.modules.rrhh.schemas import BajaEmpleadoIn, EmpleadoIn, EmpleadoOut, EmpleadoPatch
from src.modules.rrhh.service import RRHHService

router = APIRouter(prefix="/rrhh", tags=["rrhh"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ve = require_permission("RRHH", "empleados", "select")
_crea = require_permission("RRHH", "empleados", "insert")
_edita = require_permission("RRHH", "empleados", "update")


def _svc(session: SessionDep) -> RRHHService:
    return RRHHService(RRHHRepository(session))


ServiceDep = Annotated[RRHHService, Depends(_svc)]


@router.post("/empleados", status_code=status.HTTP_201_CREATED, response_model=EmpleadoOut)
async def crear_empleado(
    data: EmpleadoIn, svc: ServiceDep, _: Annotated[Principal, Depends(_crea)]
) -> EmpleadoOut:
    return EmpleadoOut.model_validate(await svc.crear_empleado(data))


@router.get("/empleados/{empleado_id}", response_model=EmpleadoOut)
async def obtener_empleado(
    empleado_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ve)]
) -> EmpleadoOut:
    return EmpleadoOut.model_validate(await svc._empleado_o_404(empleado_id))


@router.patch("/empleados/{empleado_id}", response_model=EmpleadoOut)
async def actualizar_empleado(
    empleado_id: int,
    data: EmpleadoPatch,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_edita)],
) -> EmpleadoOut:
    return EmpleadoOut.model_validate(await svc.actualizar_empleado(empleado_id, data))


@router.patch("/empleados/{empleado_id}/baja", response_model=EmpleadoOut)
async def dar_baja_empleado(
    empleado_id: int,
    data: BajaEmpleadoIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_edita)],
) -> EmpleadoOut:
    return EmpleadoOut.model_validate(await svc.dar_baja_empleado(empleado_id, data.fecha_baja))
