"""Router del módulo Plataforma de Datos —
`specs/010-plataforma-datos-tactico-estrategico/contracts/plataforma-datos.md`.

Ronda 1 (post-implementación): base path `/api/plataforma-datos` (el contrato
decía `/api/v1/ti/plataforma-datos`) y formato de error del proyecto — se alinea
a las convenciones reales del código, igual que la ronda 1 de 012.

RBAC: módulo `TI` (rol `Jefe_TI`). Sin lógica de negocio (Principio XI). El
endpoint de forzar corrida sólo se monta fuera de producción (FR-012).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_session
from src.core.security import CurrentPrincipal, Principal, require_permission
from src.modules.plataforma_datos.repository import PlataformaDatosRepository
from src.modules.plataforma_datos.schemas import (
    CalidadCorridaOut,
    CorridaOut,
    CorridasOut,
    EntidadModeloCreate,
    EntidadModeloOut,
    EntidadModeloPatch,
    ForzarCorridaIn,
    ForzarCorridaOut,
    PoliticaCreate,
    PoliticaOut,
    RegistroCalidadOut,
)
from src.modules.plataforma_datos.service import PlataformaDatosService

router = APIRouter(prefix="/plataforma-datos", tags=["plataforma-datos"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ve_modelo = require_permission("TI", "modelo_datos_warehouse", "select")
_edita_modelo = require_permission("TI", "modelo_datos_warehouse", "insert")
_ve_corridas = require_permission("TI", "corrida_carga", "select")
_ve_calidad = require_permission("TI", "registro_calidad_carga", "select")
_ve_politica = require_permission("TI", "politica_gobierno_datos", "select")
_edita_politica = require_permission("TI", "politica_gobierno_datos", "insert")


def _svc(session: SessionDep) -> PlataformaDatosService:
    return PlataformaDatosService(PlataformaDatosRepository(session))


ServiceDep = Annotated[PlataformaDatosService, Depends(_svc)]


# ============================================================ US1: modelo de datos
@router.get("/modelo", response_model=list[EntidadModeloOut])
async def listar_modelo(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve_modelo)]
) -> list[EntidadModeloOut]:
    return [EntidadModeloOut.model_validate(e) for e in await svc.listar_modelo()]


@router.post(
    "/modelo", status_code=status.HTTP_201_CREATED, response_model=EntidadModeloOut
)
async def registrar_entidad(
    data: EntidadModeloCreate,
    svc: ServiceDep,
    principal: CurrentPrincipal,
    _: Annotated[Principal, Depends(_edita_modelo)],
) -> EntidadModeloOut:
    return EntidadModeloOut.model_validate(
        await svc.registrar_entidad(data, empleado_id=principal.empleado_id)
    )


@router.patch("/modelo/{entidad_id}", response_model=EntidadModeloOut)
async def actualizar_entidad(
    entidad_id: int,
    data: EntidadModeloPatch,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_edita_modelo)],
) -> EntidadModeloOut:
    return EntidadModeloOut.model_validate(
        await svc.actualizar_entidad(entidad_id, data)
    )


# ============================================================ US2/US3: monitoreo de corridas
@router.get("/corridas", response_model=CorridasOut)
async def listar_corridas(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ve_corridas)],
    entidad_id: int | None = Query(default=None),
    estado: str | None = Query(default=None),
) -> CorridasOut:
    filas = await svc.listar_corridas(entidad_id=entidad_id, estado=estado)
    return CorridasOut(corridas=[CorridaOut(**f) for f in filas])


@router.get("/corridas/{corrida_id}/calidad", response_model=CalidadCorridaOut)
async def calidad_de_corrida(
    corrida_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ve_calidad)]
) -> CalidadCorridaOut:
    data = await svc.calidad_de_corrida(corrida_id)
    return CalidadCorridaOut(
        corrida_id=data["corrida_id"],
        registros=[RegistroCalidadOut.model_validate(r) for r in data["registros"]],
    )


# ============================================================ US4: política de gobierno de datos
@router.get("/politica", response_model=PoliticaOut)
async def politica_vigente(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve_politica)]
) -> PoliticaOut:
    return PoliticaOut.model_validate(await svc.politica_vigente())


@router.get("/politica/historial", response_model=list[PoliticaOut])
async def politica_historial(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve_politica)]
) -> list[PoliticaOut]:
    return [PoliticaOut.model_validate(p) for p in await svc.politica_historial()]


@router.post(
    "/politica", status_code=status.HTTP_201_CREATED, response_model=PoliticaOut
)
async def registrar_politica(
    data: PoliticaCreate,
    svc: ServiceDep,
    principal: CurrentPrincipal,
    _: Annotated[Principal, Depends(_edita_politica)],
) -> PoliticaOut:
    return PoliticaOut.model_validate(
        await svc.registrar_politica(data.texto, empleado_id=principal.empleado_id)
    )


# ============================================================ FR-012: forzar corrida (dev only)
if settings.app_env != "production":

    @router.post(
        "/corridas/forzar",
        status_code=status.HTTP_202_ACCEPTED,
        response_model=ForzarCorridaOut,
    )
    async def forzar_corrida(
        data: ForzarCorridaIn,
        svc: ServiceDep,
        _: Annotated[Principal, Depends(_edita_modelo)],
    ) -> ForzarCorridaOut:
        res = await svc.forzar_corrida(data.entidad_id, data.tipo_carga)
        return ForzarCorridaOut(**res)
