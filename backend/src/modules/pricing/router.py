"""Router del módulo Pricing — `contracts/pricing.md` (feature 003).

RBAC: módulo `Comercial` (rol principal `Jefe_Comercial`; `Encargado_Tienda` en el
listado diario de margen bajo de su tienda — FR-011). Sin lógica de negocio
(Principio XI): cada endpoint valida RBAC, delega en `PricingService` y forma la
respuesta.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.security import Principal, require_permission
from src.modules.pricing.repository import PricingRepository
from src.modules.pricing.schemas import (
    AlertaCompetenciaOut,
    CompetidorIn,
    CompetidorOut,
    ConfiguracionOut,
    ConfiguracionPatch,
    MargenBajoOut,
    MargenEfectivoOut,
    MargenObjetivoOut,
    MargenObjetivoPatch,
    PrecioCompetenciaIn,
    PrecioCompetenciaOut,
    PropuestaOut,
    RechazoIn,
    ReporteMargenOut,
    RevisionIn,
)
from src.modules.pricing.service import PricingService
from src.shared.exceptions import ForbiddenError
from src.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/pricing", tags=["pricing"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ver_margen = require_permission("Comercial", "margenes_objetivo", "select")
_edita_margen = require_permission("Comercial", "margenes_objetivo", "update")
_ver_propuestas = require_permission("Comercial", "propuesta_ajuste_precio", "select")
_resuelve_propuestas = require_permission("Comercial", "propuesta_ajuste_precio", "update")
_ver_margen_bajo = require_permission("Comercial", "revision_margen_bajo", "select")
_revisa_margen_bajo = require_permission("Comercial", "revision_margen_bajo", "insert")
_ver_competencia = require_permission("Comercial", "precio_competencia", "select")
_registra_competencia = require_permission("Comercial", "precio_competencia", "insert")
_ver_competidores = require_permission("Comercial", "competidores", "select")
_registra_competidor = require_permission("Comercial", "competidores", "insert")
_ver_config = require_permission("Comercial", "configuracion_pricing", "select")
_edita_config = require_permission("Comercial", "configuracion_pricing", "update")


def _svc(session: SessionDep) -> PricingService:
    return PricingService(PricingRepository(session))


ServiceDep = Annotated[PricingService, Depends(_svc)]


# ====================================================== márgenes objetivo
@router.get("/margenes", response_model=list[MargenObjetivoOut])
async def listar_margenes(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ver_margen)]
) -> list[MargenObjetivoOut]:
    return [MargenObjetivoOut.model_validate(m) for m in await svc.listar_margenes()]


@router.patch("/margenes/{product_category}", response_model=MargenObjetivoOut)
async def actualizar_margen(
    product_category: str,
    data: MargenObjetivoPatch,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_edita_margen)],
) -> MargenObjetivoOut:
    margen = await svc.definir_margen_objetivo(
        product_category,
        margen_objetivo_pct=data.margen_objetivo_pct,
        factor_sensibilidad=data.factor_sensibilidad,
    )
    return MargenObjetivoOut.model_validate(margen)


# ====================================================== margen efectivo
@router.get("/productos/{product_id}/margen-efectivo", response_model=MargenEfectivoOut)
async def margen_efectivo(
    product_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver_margen)]
) -> MargenEfectivoOut:
    return MargenEfectivoOut(**await svc.margen_objetivo_efectivo(product_id))


# ====================================================== propuestas de ajuste
@router.get("/propuestas", response_model=Page[PropuestaOut])
async def listar_propuestas(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_propuestas)],
    params: Annotated[PageParams, Depends(page_params)],
    estado: str | None = None,
    product_category: str | None = None,
) -> Page[PropuestaOut]:
    page = await svc.listar_propuestas(params, estado=estado, product_category=product_category)
    return Page(
        items=[PropuestaOut.model_validate(p) for p in page.items],
        total=page.total,
        page=page.page,
        size=page.size,
    )


@router.get("/propuestas/{propuesta_id}", response_model=PropuestaOut)
async def detalle_propuesta(
    propuesta_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver_propuestas)]
) -> PropuestaOut:
    return PropuestaOut.model_validate(await svc.get_propuesta(propuesta_id))


@router.post("/propuestas/{propuesta_id}/aprobar", response_model=PropuestaOut)
async def aprobar_propuesta(
    propuesta_id: int,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_resuelve_propuestas)],
) -> PropuestaOut:
    return PropuestaOut.model_validate(
        await svc.aprobar_propuesta(propuesta_id, principal.empleado_id)
    )


@router.post("/propuestas/{propuesta_id}/rechazar", response_model=PropuestaOut)
async def rechazar_propuesta(
    propuesta_id: int,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_resuelve_propuestas)],
    data: RechazoIn | None = None,
) -> PropuestaOut:
    motivo = data.motivo if data else None
    return PropuestaOut.model_validate(
        await svc.rechazar_propuesta(propuesta_id, principal.empleado_id, motivo)
    )


# ====================================================== margen bajo (US3)
@router.get("/margen-bajo", response_model=Page[MargenBajoOut])
async def listar_margen_bajo(
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_ver_margen_bajo)],
    params: Annotated[PageParams, Depends(page_params)],
    tienda_id: int | None = None,
    revisado: bool | None = None,
) -> Page[MargenBajoOut]:
    # FR-011: el Encargado_Tienda sólo ve su propia tienda.
    if principal.rol == "Encargado_Tienda":
        if tienda_id is not None and tienda_id != principal.tienda_id:
            raise ForbiddenError("Sólo puede consultar el margen bajo de su propia tienda")
        tienda_id = principal.tienda_id
    data = await svc.listar_margen_bajo(params, tienda_id=tienda_id, revisado=revisado)
    return Page(
        items=[MargenBajoOut(**row) for row in data["items"]],
        total=data["total"],
        page=data["page"],
        size=data["size"],
    )


@router.post("/margen-bajo/{venta_detalle_id}/revision", status_code=status.HTTP_200_OK)
async def registrar_revision(
    venta_detalle_id: int,
    data: RevisionIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_revisa_margen_bajo)],
) -> dict:
    await svc.registrar_revision(venta_detalle_id, principal.empleado_id, data.accion_correctiva)
    return {"venta_detalle_id": venta_detalle_id, "revisado": True}


# ====================================================== reporte de margen
@router.get("/reportes/margen", response_model=ReporteMargenOut)
async def reporte_margen(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_margen)],
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    product_category: str | None = None,
) -> ReporteMargenOut:
    data = await svc.reporte_margen(fecha_desde, fecha_hasta, product_category)
    return ReporteMargenOut(**data)


# ====================================================== competencia (US5)
@router.get("/competidores", response_model=list[CompetidorOut])
async def listar_competidores(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_competidores)],
    tipo: str | None = None,
    ciudad: str | None = None,
) -> list[CompetidorOut]:
    return [
        CompetidorOut.model_validate(c)
        for c in await svc.listar_competidores(tipo=tipo, ciudad=ciudad)
    ]


@router.post("/competidores", status_code=status.HTTP_201_CREATED, response_model=CompetidorOut)
async def registrar_competidor(
    data: CompetidorIn, svc: ServiceDep, _: Annotated[Principal, Depends(_registra_competidor)]
) -> CompetidorOut:
    return CompetidorOut.model_validate(await svc.registrar_competidor(data))


@router.post(
    "/productos/{product_id}/precio-competencia",
    status_code=status.HTTP_201_CREATED,
    response_model=PrecioCompetenciaOut,
)
async def registrar_precio_competencia(
    product_id: int,
    data: PrecioCompetenciaIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_registra_competencia)],
) -> PrecioCompetenciaOut:
    fila = await svc.registrar_precio_competencia_manual(product_id, data, principal.empleado_id)
    return PrecioCompetenciaOut.model_validate(fila)


@router.get(
    "/productos/{product_id}/precio-competencia",
    response_model=list[PrecioCompetenciaOut],
)
async def historial_precio_competencia(
    product_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver_competencia)]
) -> list[PrecioCompetenciaOut]:
    return [
        PrecioCompetenciaOut.model_validate(f) for f in await svc.precios_competencia_de(product_id)
    ]


@router.get("/competencia/alertas", response_model=Page[AlertaCompetenciaOut])
async def alertas_competencia(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_competencia)],
    params: Annotated[PageParams, Depends(page_params)],
    umbral: float | None = None,
) -> Page[AlertaCompetenciaOut]:
    from decimal import Decimal

    alertas = await svc.alertas_competencia(Decimal(str(umbral)) if umbral is not None else None)
    inicio, fin = params.offset, params.offset + params.limit
    return Page(
        items=[AlertaCompetenciaOut(**a) for a in alertas[inicio:fin]],
        total=len(alertas),
        page=params.page,
        size=params.size,
    )


# ====================================================== configuración
@router.get("/configuracion", response_model=list[ConfiguracionOut])
async def listar_configuracion(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ver_config)]
) -> list[ConfiguracionOut]:
    return [ConfiguracionOut.model_validate(c) for c in await svc.listar_configuracion()]


@router.patch("/configuracion/{clave}", response_model=ConfiguracionOut)
async def actualizar_configuracion(
    clave: str,
    data: ConfiguracionPatch,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_edita_config)],
) -> ConfiguracionOut:
    return ConfiguracionOut.model_validate(await svc.actualizar_configuracion(clave, data.valor))
