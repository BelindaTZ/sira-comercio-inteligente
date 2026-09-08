"""Router del módulo Traslados —
`specs/012-traslados-stock-entre-tiendas/contracts/traslados-stock-entre-tiendas.md`.

RBAC: módulo `Operaciones` (ya reservado por 001), tabla `traslados_stock`.
`Jefe_Operaciones` opera toda la red; `Encargado_Tienda` queda limitado a su
tienda (origen para resolver, destino para recibir, propia para listar) — la
restricción de alcance se valida en la capa de servicio.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.security import CurrentPrincipal, Principal, require_permission
from src.modules.traslados.repository import TrasladosRepository
from src.modules.traslados.schemas import (
    DisponibilidadSucursalesOut,
    TrasladoCreate,
    TrasladoOut,
    TrasladoReporteItem,
    TrasladoResolucion,
)
from src.modules.traslados.service import TrasladosService

router = APIRouter(prefix="/traslados", tags=["traslados"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ve = require_permission("Operaciones", "traslados_stock", "select")
_crea = require_permission("Operaciones", "traslados_stock", "insert")
_edita = require_permission("Operaciones", "traslados_stock", "update")


def _svc(session: SessionDep) -> TrasladosService:
    return TrasladosService(TrasladosRepository(session))


ServiceDep = Annotated[TrasladosService, Depends(_svc)]


# ============================================================ US1: disponibilidad
@router.get(
    "/productos/{product_id}/disponibilidad-sucursales",
    response_model=DisponibilidadSucursalesOut,
)
async def disponibilidad_sucursales(
    product_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ve)]
) -> DisponibilidadSucursalesOut:
    return DisponibilidadSucursalesOut(**await svc.disponibilidad_sucursales(product_id))


# ============================================================ US1/US3: reporte semanal
@router.get("/reporte-semanal", response_model=list[TrasladoReporteItem])
async def reporte_semanal(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ve)],
    desde: date = Query(...),
    hasta: date = Query(...),
) -> list[TrasladoReporteItem]:
    return [
        TrasladoReporteItem(
            **TrasladoOut.model_validate(t).model_dump(),
            pendiente_confirmacion=(t.estado == "en_transito"),
        )
        for t in await svc.reporte_semanal(desde, hasta)
    ]


# ============================================================ US2: solicitud / listado
@router.post("", status_code=status.HTTP_201_CREATED, response_model=TrasladoOut)
async def registrar_solicitud(
    data: TrasladoCreate,
    svc: ServiceDep,
    principal: CurrentPrincipal,
    _: Annotated[Principal, Depends(_crea)],
) -> TrasladoOut:
    return TrasladoOut.model_validate(
        await svc.registrar_solicitud(data, empleado_id=principal.empleado_id)
    )


@router.get("", response_model=list[TrasladoOut])
async def listar_traslados(
    svc: ServiceDep,
    principal: CurrentPrincipal,
    _: Annotated[Principal, Depends(_ve)],
    estado: str | None = Query(default=None),
    tienda_origen_id: int | None = Query(default=None),
) -> list[TrasladoOut]:
    filas = await svc.listar(
        estado=estado,
        tienda_origen_id=tienda_origen_id,
        rol=principal.rol,
        tienda_actor=principal.tienda_id,
    )
    return [TrasladoOut.model_validate(t) for t in filas]


# ============================================================ US2: resolución
@router.patch("/{traslado_id}/resolucion", response_model=TrasladoOut)
async def resolver_traslado(
    traslado_id: int,
    data: TrasladoResolucion,
    svc: ServiceDep,
    principal: CurrentPrincipal,
    _: Annotated[Principal, Depends(_edita)],
) -> TrasladoOut:
    return TrasladoOut.model_validate(
        await svc.resolver(
            traslado_id,
            decision=data.decision,
            motivo=data.motivo,
            rol=principal.rol,
            empleado_actor=principal.empleado_id,
            tienda_actor=principal.tienda_id,
        )
    )


# ============================================================ US3: recepción
@router.patch("/{traslado_id}/recepcion", response_model=TrasladoOut)
async def confirmar_recepcion(
    traslado_id: int,
    svc: ServiceDep,
    principal: CurrentPrincipal,
    _: Annotated[Principal, Depends(_edita)],
) -> TrasladoOut:
    return TrasladoOut.model_validate(
        await svc.confirmar_recepcion(
            traslado_id,
            rol=principal.rol,
            empleado_actor=principal.empleado_id,
            tienda_actor=principal.tienda_id,
        )
    )


# ============================================================ US2/US3: cancelación
@router.patch("/{traslado_id}/cancelacion", response_model=TrasladoOut)
async def cancelar_traslado(
    traslado_id: int,
    svc: ServiceDep,
    principal: CurrentPrincipal,
    _: Annotated[Principal, Depends(_edita)],
) -> TrasladoOut:
    return TrasladoOut.model_validate(
        await svc.cancelar(traslado_id, rol=principal.rol, empleado_actor=principal.empleado_id)
    )
