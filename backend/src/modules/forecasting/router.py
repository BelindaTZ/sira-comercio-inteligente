"""Router del módulo Forecasting — `contracts/pronostico.md` (feature 004).

RBAC: módulo `TI` (rol `Jefe_TI`) para modelos, monitoreo y configuración;
módulo `Operaciones` (rol `Jefe_Operaciones`) para el reporte de demanda perdida.
Sin lógica de negocio (Principio XI). Los endpoints "forzar corrida" sólo se
montan fuera de producción (research.md Decisión 8).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_session
from src.core.security import Principal, require_permission
from src.modules.forecasting.repository import ForecastingRepository
from src.modules.forecasting.schemas import (
    AlertaMonitoreoOut,
    ConfiguracionOut,
    ConfiguracionPatch,
    DecisionModeloIn,
    DemandaPerdidaFila,
    DemandaPerdidaProducto,
    ModeloDetalleOut,
    ModeloOut,
    MonitoreoOut,
    OpcionProductoPronostico,
    OpcionTiendaPronostico,
    PronosticoOut,
    RechazoModeloIn,
)
from src.modules.forecasting.service import ForecastingService

router = APIRouter(prefix="/forecasting", tags=["forecasting"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ver_modelo = require_permission("TI", "modelo_demanda", "select")
_decide_modelo = require_permission("TI", "modelo_demanda", "update")
_ver_monitoreo = require_permission("TI", "monitoreo_precision_modelo", "select")
_ver_pronostico = require_permission("TI", "pronostico_demanda", "select")
_ver_config = require_permission("TI", "configuracion_pronostico", "select")
_edita_config = require_permission("TI", "configuracion_pronostico", "update")
_ver_demanda_perdida = require_permission("Operaciones", "eventos_quiebre_stock", "select")


def _svc(session: SessionDep) -> ForecastingService:
    return ForecastingService(ForecastingRepository(session))


ServiceDep = Annotated[ForecastingService, Depends(_svc)]


# =================================================== modelos (FR-001 a FR-005)
@router.get("/modelos", response_model=list[ModeloOut])
async def listar_modelos(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_modelo)],
    estado: str | None = None,
) -> list[ModeloOut]:
    return [ModeloOut.model_validate(m) for m in await svc.listar_modelos(estado)]


@router.get("/modelos/{modelo_id}", response_model=ModeloDetalleOut)
async def detalle_modelo(
    modelo_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver_modelo)]
) -> ModeloDetalleOut:
    return ModeloDetalleOut(**await svc.detalle_modelo(modelo_id))


@router.post("/modelos/{modelo_id}/aprobar", response_model=ModeloOut)
async def aprobar_modelo(
    modelo_id: int,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_decide_modelo)],
    data: DecisionModeloIn | None = None,
) -> ModeloOut:
    obs = data.observaciones if data else None
    return ModeloOut.model_validate(await svc.aprobar_modelo(modelo_id, principal.empleado_id, obs))


@router.post("/modelos/{modelo_id}/rechazar", response_model=ModeloOut)
async def rechazar_modelo(
    modelo_id: int,
    data: RechazoModeloIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_decide_modelo)],
) -> ModeloOut:
    return ModeloOut.model_validate(
        await svc.rechazar_modelo(modelo_id, principal.empleado_id, data.observaciones)
    )


# =================================================== consulta de pronóstico
@router.get("/pronostico/productos", response_model=list[OpcionProductoPronostico])
async def opciones_producto_pronostico(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_pronostico)],
    search: str | None = None,
) -> list[OpcionProductoPronostico]:
    """Autocompletado: productos que el modelo vigente pronostica (por nombre o id)."""
    return [
        OpcionProductoPronostico(**o) for o in await svc.opciones_producto_pronostico(search)
    ]


@router.get("/pronostico/tiendas", response_model=list[OpcionTiendaPronostico])
async def opciones_tienda_pronostico(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ver_pronostico)]
) -> list[OpcionTiendaPronostico]:
    return [OpcionTiendaPronostico(**o) for o in await svc.opciones_tienda_pronostico()]


@router.get("/productos/{product_id}/tiendas/{tienda_id}/pronostico", response_model=PronosticoOut)
async def consultar_pronostico(
    product_id: int,
    tienda_id: int,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_pronostico)],
    semana: int = Query(...),
    anio: int = Query(...),
) -> PronosticoOut:
    return PronosticoOut(**await svc.consulta_pronostico(product_id, tienda_id, semana, anio))


# =================================================== monitoreo (FR-011 a FR-013)
@router.get("/modelos/{modelo_id}/monitoreo", response_model=list[MonitoreoOut])
async def monitoreo_modelo(
    modelo_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver_monitoreo)]
) -> list[MonitoreoOut]:
    return [MonitoreoOut.model_validate(m) for m in await svc.monitoreo_de_modelo(modelo_id)]


@router.get("/monitoreo/alertas", response_model=list[AlertaMonitoreoOut])
async def alertas_monitoreo(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ver_monitoreo)]
) -> list[AlertaMonitoreoOut]:
    return [
        AlertaMonitoreoOut(
            modelo_id=m.modelo_id,
            semana=m.semana,
            anio=m.anio,
            metrica_precision=m.metrica_precision,
        )
        for m in await svc.alertas_monitoreo()
    ]


# =================================================== demanda perdida (FR-014)
@router.get("/reportes/demanda-perdida", response_model=list[DemandaPerdidaFila])
async def reporte_demanda_perdida(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_demanda_perdida)],
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    tienda_id: int | None = None,
) -> list[DemandaPerdidaFila]:
    filas = await svc.reporte_demanda_perdida(fecha_desde, fecha_hasta, tienda_id)
    return [DemandaPerdidaFila(**f) for f in filas]


@router.get(
    "/reportes/demanda-perdida/por-producto", response_model=list[DemandaPerdidaProducto]
)
async def reporte_demanda_perdida_por_producto(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_demanda_perdida)],
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    tienda_id: int | None = None,
) -> list[DemandaPerdidaProducto]:
    """Demanda perdida por SKU (no sólo por categoría) — cada fila lleva un
    `product_id` real para poder disparar la solicitud de reposición."""
    filas = await svc.reporte_demanda_perdida_por_producto(fecha_desde, fecha_hasta, tienda_id)
    return [DemandaPerdidaProducto(**f) for f in filas]


# =================================================== configuración
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


# =================================================== forzar corrida (dev only)
if settings.app_env != "production":

    @router.post("/modelos/entrenar", status_code=status.HTTP_201_CREATED)
    async def forzar_entrenamiento(
        svc: ServiceDep, _: Annotated[Principal, Depends(_decide_modelo)]
    ) -> dict:
        return await svc.entrenar_modelo()

    @router.post("/monitoreo/calcular", status_code=status.HTTP_201_CREATED)
    async def forzar_monitoreo(
        svc: ServiceDep,
        _: Annotated[Principal, Depends(_ver_monitoreo)],
        semana: int | None = None,
        anio: int | None = None,
    ) -> dict:
        return await svc.calcular_monitoreo_semanal(semana, anio)
