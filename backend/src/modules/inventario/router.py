"""Router del módulo Inventario — `contracts/inventario.md` (US2, T042).

RBAC: módulo `Operaciones`. Reponedor registra recepciones/ajustes/mermas;
Encargado_Tienda valida mermas.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.security import Principal, require_permission
from src.modules.inventario.repository import InventarioRepository
from src.modules.inventario.schemas import (
    AjusteIn,
    AjusteOut,
    AlertaOut,
    AtenderAlertaIn,
    LoteOut,
    MermaIn,
    MermaOut,
    ProductoBusquedaOut,
    QuiebreIn,
    QuiebreOut,
    RecepcionIn,
    RecepcionOut,
    StockMaximoIn,
    StockMaximoOut,
    ValidarMermaIn,
    VerificacionAnaquelIn,
    VerificacionAnaquelOut,
)
from src.modules.inventario.service import InventarioService
from src.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/inventario", tags=["inventario"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ver = require_permission("Operaciones", "lotes", "select")
_recepcion = require_permission("Operaciones", "recepcion_mercaderia", "insert")
_ajuste = require_permission("Operaciones", "ajustes_inventario", "insert")
_merma_insert = require_permission("Operaciones", "mermas", "insert")
_merma_validar = require_permission("Operaciones", "mermas", "update")
_alerta_ver = require_permission("Operaciones", "alertas_inventario", "select")
_alerta_atender = require_permission("Operaciones", "alertas_inventario", "update")
_quiebre = require_permission("Operaciones", "eventos_quiebre_stock", "insert")
_stock_max = require_permission("Operaciones", "stock_maximo_categoria", "insert")
_anaquel = require_permission("Operaciones", "verificacion_anaquel", "insert")


def _svc(session: SessionDep) -> InventarioService:
    return InventarioService(InventarioRepository(session))


ServiceDep = Annotated[InventarioService, Depends(_svc)]


def _merma_out(merma) -> MermaOut:
    return MermaOut(
        merma_id=merma.merma_id,
        product_id=merma.product_id,
        tienda_id=merma.tienda_id,
        lote_id=merma.lote_id,
        cantidad=merma.cantidad,
        causa=merma.causa,
        valor=merma.valor,
        empleado_id=merma.empleado_id,
        estado_validacion=merma.estado_validacion,
        empleado_valida_id=merma.empleado_valida_id,
        fecha_validacion=merma.fecha_validacion,
    )


@router.post("/recepciones", status_code=status.HTTP_201_CREATED, response_model=RecepcionOut)
async def registrar_recepcion(
    data: RecepcionIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_recepcion)],
) -> RecepcionOut:
    res = await svc.registrar_recepcion(data, principal.empleado_id)
    return RecepcionOut(**res)


@router.get("/lotes", response_model=Page[LoteOut])
async def listar_lotes(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver)],
    params: Annotated[PageParams, Depends(page_params)],
    product_id: int | None = None,
    tienda_id: int | None = None,
    proximos_a_vencer: bool = False,
    dias: int = Query(default=7, ge=1),
    search: str | None = None,
) -> Page[LoteOut]:
    res = await svc.listar_lotes(
        params,
        product_id=product_id,
        tienda_id=tienda_id,
        proximos_a_vencer=proximos_a_vencer,
        dias=dias,
        search=search,
    )
    return Page[LoteOut](**res)


@router.get("/productos", response_model=list[ProductoBusquedaOut])
async def buscar_productos(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver)],
    q: Annotated[str, Query(min_length=1)],
) -> list[ProductoBusquedaOut]:
    """Autocompletado de producto para los formularios de operación (ajuste,
    merma, verificación de anaquel): acepta nombre o id."""
    return [ProductoBusquedaOut.model_validate(p) for p in await svc.buscar_productos(q)]


@router.post("/ajustes", status_code=status.HTTP_201_CREATED, response_model=AjusteOut)
async def registrar_ajuste(
    data: AjusteIn, svc: ServiceDep, _: Annotated[Principal, Depends(_ajuste)]
) -> AjusteOut:
    return AjusteOut(**await svc.registrar_ajuste(data))


@router.post("/mermas", status_code=status.HTTP_201_CREATED, response_model=MermaOut)
async def registrar_merma(
    data: MermaIn, svc: ServiceDep, _: Annotated[Principal, Depends(_merma_insert)]
) -> MermaOut:
    return _merma_out(await svc.registrar_merma(data))


@router.post("/mermas/{merma_id}/validar", response_model=MermaOut)
async def validar_merma(
    merma_id: int,
    data: ValidarMermaIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_merma_validar)],
) -> MermaOut:
    return _merma_out(await svc.validar_merma(merma_id, data))


# ------------------------------------------------------------------- US3: alertas
@router.get("/alertas", response_model=Page[AlertaOut])
async def listar_alertas(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_alerta_ver)],
    params: Annotated[PageParams, Depends(page_params)],
    tipo: str | None = None,
    estado: str | None = "pendiente",
    tienda_id: int | None = None,
    search: str | None = None,
) -> Page[AlertaOut]:
    page = await svc.listar_alertas(
        params, tipo=tipo, estado=estado, tienda_id=tienda_id, search=search
    )
    return Page[AlertaOut](
        items=[AlertaOut.model_validate(a) for a in page.items],
        total=page.total,
        page=page.page,
        size=page.size,
    )


@router.post("/alertas/{alerta_id}/atender", response_model=AlertaOut)
async def atender_alerta(
    alerta_id: int,
    data: AtenderAlertaIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_alerta_atender)],
) -> AlertaOut:
    return AlertaOut.model_validate(await svc.atender_alerta(alerta_id, data))


@router.post("/jobs/reposicion")
async def job_reposicion(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_alerta_atender)],
    tienda_id: int | None = None,
) -> dict:
    """Ejecución manual del job diario de punto de reposición (FR-020)."""
    return {"alertas_generadas": await svc.ejecutar_job_reposicion(tienda_id)}


@router.post("/jobs/vencimiento")
async def job_vencimiento(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_alerta_atender)],
    tienda_id: int | None = None,
) -> dict:
    """Ejecución manual del job de alertas de vencimiento (FR-016)."""
    return {"alertas_generadas": await svc.ejecutar_job_vencimiento(tienda_id)}


# ------------------------------------------------------------------- US3: quiebre
@router.post("/quiebres", status_code=status.HTTP_201_CREATED, response_model=QuiebreOut)
async def registrar_quiebre(
    data: QuiebreIn, svc: ServiceDep, _: Annotated[Principal, Depends(_quiebre)]
) -> QuiebreOut:
    return QuiebreOut.model_validate(await svc.registrar_quiebre(data))


# -------------------------------------------------------- US3: stock máximo (R9)
@router.put("/stock-maximo", response_model=StockMaximoOut)
async def definir_stock_maximo(
    data: StockMaximoIn, svc: ServiceDep, _: Annotated[Principal, Depends(_stock_max)]
) -> StockMaximoOut:
    return StockMaximoOut.model_validate(await svc.definir_stock_maximo(data))


@router.get("/stock-maximo", response_model=Page[StockMaximoOut])
async def listar_stock_maximo(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver)],
    params: Annotated[PageParams, Depends(page_params)],
    tienda_id: int = Query(...),
    product_category: str | None = None,
) -> Page[StockMaximoOut]:
    page = await svc.listar_stock_maximo(
        params, tienda_id=tienda_id, product_category=product_category
    )
    return Page[StockMaximoOut](
        items=[StockMaximoOut.model_validate(s) for s in page.items],
        total=page.total,
        page=page.page,
        size=page.size,
    )


# ------------------------------------------ US3: verificación de anaquel (R10)
@router.post(
    "/verificacion-anaquel",
    status_code=status.HTTP_201_CREATED,
    response_model=VerificacionAnaquelOut,
)
async def registrar_verificacion_anaquel(
    data: VerificacionAnaquelIn, svc: ServiceDep, _: Annotated[Principal, Depends(_anaquel)]
) -> VerificacionAnaquelOut:
    return VerificacionAnaquelOut.model_validate(await svc.registrar_verificacion_anaquel(data))
