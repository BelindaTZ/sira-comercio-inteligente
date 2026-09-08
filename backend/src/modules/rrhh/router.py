"""Router del módulo RRHH.

CRUD base de empleado: `contracts/auth-administracion-sistema.md` (008).
Puestos críticos, retención, capacitación, clima laboral y plan de sucesión:
`specs/011-recursos-humanos/contracts/recursos-humanos.md`.

RBAC: módulo `RRHH`. `Jefe_RRHH` administra todo; `Encargado_Tienda` tiene un
acceso concedido de solo lectura (`empleado_capacitacion`) para el cumplimiento de
capacitación de su propio personal (FR-005) — restringido a su tienda en el
servicio.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.security import CurrentPrincipal, Principal, require_permission
from src.modules.rrhh.repository import RRHHRepository
from src.modules.rrhh.schemas import (
    AccionRetencionIn,
    AccionRetencionOut,
    BajaEmpleadoIn,
    CapacitacionIn,
    CapacitacionOut,
    ClimaLaboralIn,
    ClimaLaboralOut,
    ClimaRotacionOut,
    CoberturaSucesionItem,
    CompletarCapacitacionIn,
    CumplimientoCapacitacionItem,
    EmpleadoCapacitacionOut,
    EmpleadoIn,
    EmpleadoOut,
    EmpleadoPatch,
    MarcarCriticoIn,
    PlanSucesionIn,
    PlanSucesionOut,
    PuestoOut,
)
from src.modules.rrhh.service import RRHHService

router = APIRouter(prefix="/rrhh", tags=["rrhh"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ve = require_permission("RRHH", "empleados", "select")
_crea = require_permission("RRHH", "empleados", "insert")
_edita = require_permission("RRHH", "empleados", "update")
_marca_critico = require_permission("RRHH", "roles_puesto", "update")
_ve_retencion = require_permission("RRHH", "acciones_retencion", "select")
_crea_retencion = require_permission("RRHH", "acciones_retencion", "insert")
_crea_capacitacion = require_permission("RRHH", "capacitaciones", "insert")
_edita_capacitacion = require_permission("RRHH", "empleado_capacitacion", "update")
_ve_capacitacion = require_permission("RRHH", "empleado_capacitacion", "select")
_crea_clima = require_permission("RRHH", "clima_laboral", "insert")
_ve_clima = require_permission("RRHH", "clima_laboral", "select")
_crea_sucesion = require_permission("RRHH", "plan_sucesion", "insert")
_ve_sucesion = require_permission("RRHH", "plan_sucesion", "select")

_ENCARGADO = "Encargado_Tienda"


def _svc(session: SessionDep) -> RRHHService:
    return RRHHService(RRHHRepository(session))


ServiceDep = Annotated[RRHHService, Depends(_svc)]


# ============================================================ 008: empleados
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


# ============================================================ 011 US1: puestos críticos / retención
@router.patch("/puestos/{puesto_id}/critico", response_model=PuestoOut)
async def marcar_puesto_critico(
    puesto_id: int,
    data: MarcarCriticoIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_marca_critico)],
) -> PuestoOut:
    return PuestoOut.model_validate(await svc.marcar_puesto_critico(puesto_id, data.es_critico))


@router.post(
    "/acciones-retencion", status_code=status.HTTP_201_CREATED, response_model=AccionRetencionOut
)
async def registrar_accion_retencion(
    data: AccionRetencionIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_crea_retencion)],
) -> AccionRetencionOut:
    return AccionRetencionOut.model_validate(
        await svc.registrar_accion_retencion(
            empleado_id=data.empleado_id, fecha=data.fecha, descripcion=data.descripcion
        )
    )


@router.get("/empleados/{empleado_id}/acciones-retencion", response_model=list[AccionRetencionOut])
async def listar_acciones_retencion(
    empleado_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ve_retencion)]
) -> list[AccionRetencionOut]:
    return [AccionRetencionOut.model_validate(a) for a in await svc.acciones_retencion(empleado_id)]


# ============================================================ 011 US2: capacitación
@router.post("/capacitaciones", status_code=status.HTTP_201_CREATED, response_model=CapacitacionOut)
async def programar_capacitacion(
    data: CapacitacionIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_crea_capacitacion)],
) -> CapacitacionOut:
    return CapacitacionOut(
        **await svc.programar_capacitacion(
            nombre=data.nombre, descripcion=data.descripcion, role_ids=data.role_ids
        )
    )


@router.patch(
    "/empleado-capacitacion/{empleado_id}/{capacitacion_id}/completar",
    response_model=EmpleadoCapacitacionOut,
)
async def completar_capacitacion(
    empleado_id: int,
    capacitacion_id: int,
    data: CompletarCapacitacionIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_edita_capacitacion)],
) -> EmpleadoCapacitacionOut:
    return EmpleadoCapacitacionOut.model_validate(
        await svc.confirmar_cumplimiento(
            empleado_id=empleado_id,
            capacitacion_id=capacitacion_id,
            fecha_completado=data.fecha_completado,
            tienda_actor=None,
            restringir_a_tienda=False,
        )
    )


@router.get(
    "/tiendas/{tienda_id}/cumplimiento-capacitacion",
    response_model=list[CumplimientoCapacitacionItem],
)
async def cumplimiento_capacitacion_tienda(
    tienda_id: int,
    svc: ServiceDep,
    principal: CurrentPrincipal,
    _: Annotated[Principal, Depends(_ve_capacitacion)],
) -> list[CumplimientoCapacitacionItem]:
    es_encargado = principal.rol == _ENCARGADO
    filas = await svc.cumplimiento_tienda(
        tienda_id,
        tienda_actor=principal.tienda_id,
        restringir_a_tienda=es_encargado,
    )
    return [CumplimientoCapacitacionItem(**f) for f in filas]


# ============================================================ 011 US3: clima / rotación
@router.post("/clima-laboral", status_code=status.HTTP_201_CREATED, response_model=ClimaLaboralOut)
async def registrar_clima(
    data: ClimaLaboralIn, svc: ServiceDep, _: Annotated[Principal, Depends(_crea_clima)]
) -> ClimaLaboralOut:
    return ClimaLaboralOut.model_validate(
        await svc.registrar_clima(
            tienda_id=data.tienda_id,
            periodo=data.periodo,
            resultado_promedio=data.resultado_promedio,
        )
    )


@router.get("/tiendas/{tienda_id}/clima-rotacion", response_model=ClimaRotacionOut)
async def clima_rotacion(
    tienda_id: int,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ve_clima)],
    periodo: str = Query(..., pattern=r"^\d{4}-S[12]$"),
) -> ClimaRotacionOut:
    return ClimaRotacionOut(**await svc.clima_rotacion(tienda_id, periodo))


# ============================================================ 011 US4: plan de sucesión
@router.post("/plan-sucesion", status_code=status.HTTP_201_CREATED, response_model=PlanSucesionOut)
async def registrar_candidato_sucesion(
    data: PlanSucesionIn, svc: ServiceDep, _: Annotated[Principal, Depends(_crea_sucesion)]
) -> PlanSucesionOut:
    return PlanSucesionOut.model_validate(
        await svc.registrar_candidato_sucesion(
            puesto_id=data.puesto_id, empleado_candidato_id=data.empleado_candidato_id
        )
    )


@router.get("/plan-sucesion/cobertura", response_model=list[CoberturaSucesionItem])
async def cobertura_sucesion(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve_sucesion)]
) -> list[CoberturaSucesionItem]:
    return [CoberturaSucesionItem(**p) for p in await svc.cobertura_sucesion()]
