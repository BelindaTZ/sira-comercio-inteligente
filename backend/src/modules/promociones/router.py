"""Router del módulo Promociones — `contracts/promociones.md` (feature 005).

RBAC: módulo `Marketing_CRM` (Jefe_Marketing) para afinidad, cupones y colocación;
módulo `Operaciones` (Jefe_Operaciones / Encargado_Tienda) para clasificación ABC
y liquidación; módulo `Ventas` (Cajero) para la recomendación de cross-sell. Sin
lógica de negocio (Principio XI). Los endpoints "forzar corrida" sólo se montan
fuera de producción (research.md Decisión 10).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_session
from src.core.security import Principal, require_permission
from src.modules.promociones.repository import PromocionesRepository
from src.modules.promociones.schemas import (
    CambioAbcOut,
    CandidatoLiquidacionOut,
    ColocacionIn,
    ColocacionOut,
    CuponAfinidadOut,
    DesactivarReglaIn,
    EfectoColocacionOut,
    RecomendacionOut,
    ReglaAfinidadOut,
    ReglaLiquidacionOut,
    ReglaLiquidacionPatch,
    TasaRedencionAfinidadOut,
)
from src.modules.promociones.service import PromocionesService

router = APIRouter(prefix="/promociones", tags=["promociones"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ver_reglas = require_permission("Marketing_CRM", "regla_afinidad", "select")
_edita_reglas = require_permission("Marketing_CRM", "regla_afinidad", "update")
_recomienda = require_permission("Ventas", "regla_afinidad", "select")
_ver_cupones = require_permission("Marketing_CRM", "cupon_enviado", "select")
_ver_abc = require_permission("Operaciones", "cambio_clasificacion_abc", "select")
_calcula_abc = require_permission("Operaciones", "productos", "update")
_ver_liquidacion = require_permission("Operaciones", "configuracion_promociones", "select")
_edita_liquidacion = require_permission("Operaciones", "configuracion_promociones", "update")
_ver_candidatos = require_permission("Operaciones", "candidato_liquidacion", "select")
_ejecuta_candidato = require_permission("Operaciones", "candidato_liquidacion", "update")
_ver_colocacion = require_permission("Marketing_CRM", "promociones", "select")
_registra_colocacion = require_permission("Marketing_CRM", "promociones", "insert")


def _svc(session: SessionDep) -> PromocionesService:
    return PromocionesService(PromocionesRepository(session))


ServiceDep = Annotated[PromocionesService, Depends(_svc)]


# ==================================================== afinidad (FR-001 a FR-005)
@router.get("/reglas-afinidad", response_model=list[ReglaAfinidadOut])
async def listar_reglas(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ver_reglas)], estado: str | None = None
) -> list[ReglaAfinidadOut]:
    return [ReglaAfinidadOut.model_validate(r) for r in await svc.listar_reglas(estado)]


@router.post("/reglas-afinidad/{regla_id}/desactivar", response_model=ReglaAfinidadOut)
async def desactivar_regla(
    regla_id: int,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_edita_reglas)],
    data: DesactivarReglaIn | None = None,
) -> ReglaAfinidadOut:
    motivo = data.motivo if data else None
    return ReglaAfinidadOut.model_validate(
        await svc.desactivar_regla(regla_id, principal.empleado_id, motivo)
    )


@router.get("/recomendacion-cross-sell", response_model=RecomendacionOut)
async def recomendacion_cross_sell(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_recomienda)],
    product_ids: str = Query(..., description="ids separados por coma, ej. 1,2,3"),
) -> RecomendacionOut:
    ids = [int(x) for x in product_ids.split(",") if x.strip()]
    return RecomendacionOut(**await svc.recomendar_cross_sell(ids))


# ==================================================== cupón de afinidad (FR-006 a FR-008)
@router.get("/cupones-afinidad", response_model=list[CuponAfinidadOut])
async def listar_cupones_afinidad(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_cupones)],
    household_id: int | None = None,
) -> list[CuponAfinidadOut]:
    return [CuponAfinidadOut(**c) for c in await svc.listar_cupones_afinidad(household_id)]


@router.get("/cupones-afinidad/tasa-redencion", response_model=TasaRedencionAfinidadOut)
async def tasa_redencion_afinidad(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ver_cupones)]
) -> TasaRedencionAfinidadOut:
    return TasaRedencionAfinidadOut(**await svc.tasa_redencion_afinidad())


# ==================================================== clasificación ABC (FR-009, FR-010)
@router.get("/clasificacion-abc", response_model=list[CambioAbcOut])
async def clasificacion_abc(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_abc)],
    cambios_desde: datetime | None = None,
) -> list[CambioAbcOut]:
    return [CambioAbcOut.model_validate(c) for c in await svc.listar_cambios_abc(cambios_desde)]


# ==================================================== liquidación (FR-011 a FR-014)
@router.get("/liquidacion/reglas", response_model=ReglaLiquidacionOut)
async def regla_liquidacion(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ver_liquidacion)]
) -> ReglaLiquidacionOut:
    return ReglaLiquidacionOut(**await svc.regla_liquidacion())


@router.patch("/liquidacion/reglas", response_model=ReglaLiquidacionOut)
async def actualizar_regla_liquidacion(
    data: ReglaLiquidacionPatch,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_edita_liquidacion)],
) -> ReglaLiquidacionOut:
    return ReglaLiquidacionOut(
        **await svc.actualizar_regla_liquidacion(
            rotacion=data.rotacion_minima_liquidacion_semanal,
            descuento=data.descuento_liquidacion_pct,
        )
    )


@router.get("/liquidacion/candidatos", response_model=list[CandidatoLiquidacionOut])
async def listar_candidatos(
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_ver_candidatos)],
    tienda_id: int | None = None,
    semana: int | None = None,
    anio: int | None = None,
) -> list[CandidatoLiquidacionOut]:
    # El Encargado_Tienda sólo ve su propia tienda (FR-012).
    if principal.rol == "Encargado_Tienda":
        tienda_id = principal.tienda_id
    if tienda_id is None:
        return []
    return [
        CandidatoLiquidacionOut.model_validate(c)
        for c in await svc.listar_candidatos(tienda_id=tienda_id, semana=semana, anio=anio)
    ]


@router.post(
    "/liquidacion/candidatos/{candidato_id}/ejecutar", response_model=CandidatoLiquidacionOut
)
async def ejecutar_candidato(
    candidato_id: int,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_ejecuta_candidato)],
) -> CandidatoLiquidacionOut:
    return CandidatoLiquidacionOut.model_validate(
        await svc.ejecutar_candidato(candidato_id, principal.empleado_id)
    )


# ==================================================== colocación (FR-015, FR-016)
@router.get("/colocaciones", response_model=list[ColocacionOut])
async def listar_colocaciones(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_colocacion)],
    tienda_id: int | None = None,
    semana: int | None = None,
    anio: int | None = None,
) -> list[ColocacionOut]:
    return [
        ColocacionOut(**c)
        for c in await svc.listar_colocaciones(tienda_id=tienda_id, semana=semana, anio=anio)
    ]


@router.post("/colocaciones", status_code=status.HTTP_201_CREATED, response_model=ColocacionOut)
async def registrar_colocacion(
    data: ColocacionIn, svc: ServiceDep, _: Annotated[Principal, Depends(_registra_colocacion)]
) -> ColocacionOut:
    return ColocacionOut(**await svc.registrar_colocacion(data))


@router.get("/colocaciones/{promocion_id}/efecto", response_model=EfectoColocacionOut)
async def efecto_colocacion(
    promocion_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver_colocacion)]
) -> EfectoColocacionOut:
    return EfectoColocacionOut(**await svc.efecto_colocacion(promocion_id))


# ==================================================== forzar corrida (dev only)
if settings.app_env != "production":

    @router.post("/reglas-afinidad/calcular", status_code=status.HTTP_201_CREATED)
    async def forzar_afinidad(
        svc: ServiceDep, _: Annotated[Principal, Depends(_edita_reglas)]
    ) -> dict:
        return await svc.calcular_afinidad()

    @router.post("/cupones-afinidad/evaluar-venta/{venta_id}")
    async def forzar_evaluacion_venta(
        venta_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver_cupones)]
    ) -> dict:
        return await svc.evaluar_venta_para_afinidad(venta_id)

    @router.post("/clasificacion-abc/calcular", status_code=status.HTTP_201_CREATED)
    async def forzar_clasificacion(
        svc: ServiceDep, _: Annotated[Principal, Depends(_calcula_abc)]
    ) -> dict:
        return await svc.clasificar_abc()

    @router.post("/liquidacion/candidatos/calcular", status_code=status.HTTP_201_CREATED)
    async def forzar_candidatos(
        svc: ServiceDep,
        _: Annotated[Principal, Depends(_edita_liquidacion)],
        semana: int | None = None,
        anio: int | None = None,
    ) -> dict:
        return await svc.generar_candidatos_liquidacion(semana, anio)
