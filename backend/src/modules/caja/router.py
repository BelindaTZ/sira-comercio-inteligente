"""Router del módulo Caja — `contracts/caja-mermas-fraude.md` (feature 006).

RBAC: todos los endpoints viven bajo el módulo `Finanzas` (ya sembrado desde 001
como "Caja, cuadre, seguridad de pagos"). `Jefe_TI` recibe acceso a este módulo
para datáfonos y estándar de seguridad de pagos (research.md Decisión 10). Sin
lógica de negocio (Principio V/XI).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_session
from src.core.security import Principal, require_permission
from src.modules.caja.repository import CajaRepository
from src.modules.caja.schemas import (
    ActualizarDatafonoIn,
    AperturaIn,
    AperturaOut,
    AplicarProtocoloIn,
    CajaOut,
    CerrarIncidenteIn,
    CierreIn,
    CierreOut,
    CierreTiendaItem,
    ConfiguracionSeguridadOut,
    ConteoIncidentesSeguridadOut,
    DatafonoEditIn,
    DatafonoIn,
    DatafonoOut,
    DatafonoRestablecidoOut,
    DefinirEstandarSeguridadIn,
    DefinirPoliticaIn,
    DefinirProtocoloIn,
    DefinirUmbralMermaIn,
    FueraServicioIn,
    IncidenteFraudeIn,
    IncidenteFraudeOut,
    IncidenteSeguridadIn,
    IncidenteSeguridadOut,
    PoliticaSeguridadPagosOut,
    ProtocoloEscalamientoOut,
    ReporteDiferenciasOut,
    SeguimientoMermaOut,
    TransicionarIncidenteSeguridadIn,
    UmbralMermaOut,
)
from src.modules.caja.service import CajaService

router = APIRouter(prefix="/caja", tags=["caja"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_cajero_apertura = require_permission("Finanzas", "apertura_caja", "insert")
_cajero_cierre = require_permission("Finanzas", "cierre_caja", "insert")
_ve_cierres = require_permission("Finanzas", "cierre_caja", "select")
_ve_datafonos = require_permission("Finanzas", "datafonos", "select")
_edita_datafonos = require_permission("Finanzas", "datafonos", "update")
_gestiona_datafonos = require_permission("Finanzas", "datafonos", "insert")
_ve_estandar = require_permission("Finanzas", "configuracion_seguridad_pagos", "select")
_define_estandar = require_permission("Finanzas", "configuracion_seguridad_pagos", "insert")
_ve_reporte = require_permission("Finanzas", "ajustes_inventario", "select")
_gestiona_incidentes = require_permission("Finanzas", "incidentes_fraude", "insert")
_ve_incidentes = require_permission("Finanzas", "incidentes_fraude", "select")
_aplica_protocolo = require_permission("Finanzas", "incidentes_fraude", "update")
_ve_protocolo = require_permission("Finanzas", "protocolo_escalamiento", "select")
_define_protocolo = require_permission("Finanzas", "protocolo_escalamiento", "insert")
_ve_umbral = require_permission("Finanzas", "umbral_merma_categoria", "select")
_edita_umbral = require_permission("Finanzas", "umbral_merma_categoria", "update")
# feature 007
_ve_incidente_seguridad = require_permission("Finanzas", "incidente_seguridad_pago", "select")
_gestiona_incidente_seguridad = require_permission("Finanzas", "incidente_seguridad_pago", "insert")
_transiciona_incidente_seguridad = require_permission(
    "Finanzas", "incidente_seguridad_pago", "update"
)
_ve_politica = require_permission("Finanzas", "politica_seguridad_pagos", "select")
_define_politica = require_permission("Finanzas", "politica_seguridad_pagos", "insert")


def _svc(session: SessionDep) -> CajaService:
    return CajaService(CajaRepository(session))


ServiceDep = Annotated[CajaService, Depends(_svc)]


# ==================================================== apertura y cuadre (FR-001 a FR-005)
@router.post("/apertura", status_code=status.HTTP_201_CREATED, response_model=AperturaOut)
async def registrar_apertura(
    data: AperturaIn, svc: ServiceDep, principal: Annotated[Principal, Depends(_cajero_apertura)]
) -> AperturaOut:
    apertura = await svc.registrar_apertura(
        caja_id=data.caja_id,
        cajero_id=principal.empleado_id,
        fondo_inicial=data.fondo_inicial,
    )
    return AperturaOut.model_validate(apertura)


@router.post("/cierre", status_code=status.HTTP_201_CREATED, response_model=CierreOut)
async def registrar_cierre(
    data: CierreIn, svc: ServiceDep, _: Annotated[Principal, Depends(_cajero_cierre)]
) -> CierreOut:
    return CierreOut(**await svc.registrar_cierre(
        caja_id=data.caja_id, total_registrado=data.total_registrado
    ))


@router.get("/cierres", response_model=list[CierreTiendaItem])
async def listar_cierres(
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_ve_cierres)],
    tienda_id: int | None = None,
    fecha: date | None = None,
) -> list[CierreTiendaItem]:
    # El Encargado_Tienda sólo consulta su propia tienda (FR-005).
    if principal.rol == "Encargado_Tienda" or tienda_id is None:
        tienda_id = principal.tienda_id
    if tienda_id is None:
        return []
    filas = await svc.listar_cierres_tienda(tienda_id=tienda_id, dia=fecha)
    return [CierreTiendaItem(**f) for f in filas]


# ==================================================== datáfonos (FR-006 a FR-008)
@router.get("/cajas", response_model=list[CajaOut])
async def listar_cajas(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ve_datafonos)],
    tienda_id: int | None = None,
) -> list[CajaOut]:
    """Cajas de la red (o de una tienda) — para asignar un datáfono a una caja."""
    return [CajaOut.model_validate(c) for c in await svc.listar_cajas(tienda_id)]


@router.get("/datafonos", response_model=list[DatafonoOut])
async def listar_datafonos(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve_datafonos)], estado: str | None = None
) -> list[DatafonoOut]:
    return [DatafonoOut.model_validate(d) for d in await svc.listar_datafonos(estado)]


@router.post("/datafonos", status_code=status.HTTP_201_CREATED, response_model=DatafonoOut)
async def registrar_datafono(
    data: DatafonoIn, svc: ServiceDep, _: Annotated[Principal, Depends(_gestiona_datafonos)]
) -> DatafonoOut:
    """FR-006 — alta de un datáfono en el inventario (Jefe de TI)."""
    return DatafonoOut.model_validate(
        await svc.registrar_datafono(
            caja_id=data.caja_id,
            modelo=data.modelo,
            version_firmware=data.version_firmware,
            fecha_ultima_actualizacion=data.fecha_ultima_actualizacion,
        )
    )


@router.patch("/datafonos/{datafono_id}", response_model=DatafonoOut)
async def editar_datafono(
    datafono_id: int,
    data: DatafonoEditIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_gestiona_datafonos)],
) -> DatafonoOut:
    """FR-006 — edita modelo / firmware / fecha de última actualización (Jefe de
    TI). El estado de conformidad se recalcula."""
    return DatafonoOut.model_validate(
        await svc.editar_datafono(
            datafono_id,
            modelo=data.modelo,
            version_firmware=data.version_firmware,
            fecha_ultima_actualizacion=data.fecha_ultima_actualizacion,
            campos_enviados=set(data.model_fields_set),
        )
    )


@router.patch("/datafonos/{datafono_id}/actualizar", response_model=DatafonoOut)
async def actualizar_datafono(
    datafono_id: int,
    data: ActualizarDatafonoIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_edita_datafonos)],
) -> DatafonoOut:
    return DatafonoOut.model_validate(
        await svc.actualizar_datafono(datafono_id, data.version_firmware_nueva)
    )


@router.patch("/datafonos/{datafono_id}/fuera-servicio", response_model=DatafonoOut)
async def datafono_fuera_servicio(
    datafono_id: int,
    data: FueraServicioIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_edita_datafonos)],
) -> DatafonoOut:
    """FR-001 (007) — el Encargado de Tienda marca un datáfono fuera de servicio,
    con constancia del motivo (feature 013)."""
    return DatafonoOut.model_validate(
        await svc.marcar_datafono_fuera_servicio(datafono_id, data.motivo)
    )


@router.patch("/datafonos/{datafono_id}/restablecer", response_model=DatafonoRestablecidoOut)
async def datafono_restablecer(
    datafono_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_edita_datafonos)]
) -> DatafonoRestablecidoOut:
    """FR-002/FR-003 (007) — restablece un datáfono reevaluando su conformidad."""
    return DatafonoRestablecidoOut(**await svc.restablecer_datafono(datafono_id))


@router.get("/configuracion-seguridad-pagos", response_model=ConfiguracionSeguridadOut)
async def configuracion_seguridad_pagos(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve_estandar)]
) -> ConfiguracionSeguridadOut:
    return ConfiguracionSeguridadOut.model_validate(await svc.configuracion_seguridad_vigente())


@router.put(
    "/configuracion-seguridad-pagos",
    status_code=status.HTTP_201_CREATED,
    response_model=ConfiguracionSeguridadOut,
)
async def definir_estandar_seguridad(
    data: DefinirEstandarSeguridadIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_define_estandar)],
) -> ConfiguracionSeguridadOut:
    return ConfiguracionSeguridadOut.model_validate(
        await svc.definir_estandar_seguridad(
            version_minima_firmware=data.version_minima_firmware,
            actualizado_por=principal.empleado_id,
        )
    )


# ========================================= reporte mensual y escalamiento (FR-009 a FR-011)
@router.get("/reporte-diferencias", response_model=ReporteDiferenciasOut)
async def reporte_diferencias(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ve_reporte)],
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2000),
) -> ReporteDiferenciasOut:
    return ReporteDiferenciasOut(**await svc.generar_reporte_diferencias(mes=mes, anio=anio))


@router.post(
    "/incidentes-fraude", status_code=status.HTTP_201_CREATED, response_model=IncidenteFraudeOut
)
async def crear_incidente(
    data: IncidenteFraudeIn, svc: ServiceDep, _: Annotated[Principal, Depends(_gestiona_incidentes)]
) -> IncidenteFraudeOut:
    return IncidenteFraudeOut.model_validate(await svc.escalar_incidente(data))


# ==================================================== incidentes y protocolo (FR-012 a FR-016)
@router.get("/incidentes-fraude", response_model=list[IncidenteFraudeOut])
async def listar_incidentes(
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_ve_incidentes)],
    estado: str | None = None,
) -> list[IncidenteFraudeOut]:
    tienda_id = principal.tienda_id if principal.rol == "Encargado_Tienda" else None
    return [
        IncidenteFraudeOut.model_validate(i)
        for i in await svc.listar_incidentes(estado=estado, tienda_id=tienda_id)
    ]


@router.get("/protocolo-escalamiento", response_model=ProtocoloEscalamientoOut)
async def protocolo_escalamiento(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve_protocolo)]
) -> ProtocoloEscalamientoOut:
    return ProtocoloEscalamientoOut.model_validate(await svc.protocolo_vigente())


@router.get("/protocolo-escalamiento/historial", response_model=list[ProtocoloEscalamientoOut])
async def protocolo_escalamiento_historial(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve_protocolo)]
) -> list[ProtocoloEscalamientoOut]:
    """Historial de versiones del protocolo (append-only)."""
    return [
        ProtocoloEscalamientoOut.model_validate(p) for p in await svc.historial_protocolo()
    ]


@router.put(
    "/protocolo-escalamiento",
    status_code=status.HTTP_201_CREATED,
    response_model=ProtocoloEscalamientoOut,
)
async def definir_protocolo(
    data: DefinirProtocoloIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_define_protocolo)],
) -> ProtocoloEscalamientoOut:
    return ProtocoloEscalamientoOut.model_validate(
        await svc.definir_protocolo(texto=data.texto, definido_por=principal.empleado_id)
    )


@router.patch(
    "/incidentes-fraude/{incidente_id}/aplicar-protocolo", response_model=IncidenteFraudeOut
)
async def aplicar_protocolo(
    incidente_id: int,
    data: AplicarProtocoloIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_aplica_protocolo)],
) -> IncidenteFraudeOut:
    return IncidenteFraudeOut.model_validate(
        await svc.aplicar_protocolo(
            incidente_id,
            acciones_tomadas=data.acciones_tomadas,
            empleado_id=principal.empleado_id,
        )
    )


@router.patch("/incidentes-fraude/{incidente_id}/cerrar", response_model=IncidenteFraudeOut)
async def cerrar_incidente(
    incidente_id: int,
    data: CerrarIncidenteIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_gestiona_incidentes)],
) -> IncidenteFraudeOut:
    return IncidenteFraudeOut.model_validate(
        await svc.cerrar_incidente(
            incidente_id, resultado=data.resultado, empleado_id=principal.empleado_id
        )
    )


# ========================================= umbral de merma y seguimiento (FR-017 a FR-019)
@router.get("/umbral-merma", response_model=list[UmbralMermaOut])
async def listar_umbrales(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve_umbral)]
) -> list[UmbralMermaOut]:
    return [UmbralMermaOut.model_validate(u) for u in await svc.listar_umbrales()]


@router.put("/umbral-merma/{product_category:path}", response_model=UmbralMermaOut)
async def definir_umbral(
    product_category: str,
    data: DefinirUmbralMermaIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_edita_umbral)],
) -> UmbralMermaOut:
    return UmbralMermaOut.model_validate(
        await svc.definir_umbral(
            product_category=product_category,
            porcentaje_umbral=data.porcentaje_umbral,
            definido_por=principal.empleado_id,
        )
    )


@router.get(
    "/tiendas/{tienda_id}/seguimiento-merma-semanal", response_model=list[SeguimientoMermaOut]
)
async def seguimiento_merma_semanal(
    tienda_id: int,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ve_umbral)],
    semana: int = Query(..., ge=1, le=53),
    anio: int | None = None,
) -> list[SeguimientoMermaOut]:
    filas = await svc.calcular_seguimiento_semanal(tienda_id=tienda_id, semana=semana, anio=anio)
    return [SeguimientoMermaOut(**f) for f in filas]


# ========================================= incidentes de seguridad de pago (007, FR-008 a FR-011)
@router.post(
    "/incidentes-seguridad-pago",
    status_code=status.HTTP_201_CREATED,
    response_model=IncidenteSeguridadOut,
)
async def crear_incidente_seguridad(
    data: IncidenteSeguridadIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_gestiona_incidente_seguridad)],
) -> IncidenteSeguridadOut:
    return IncidenteSeguridadOut.model_validate(
        await svc.registrar_incidente_seguridad(
            datafono_id=data.datafono_id,
            descripcion=data.descripcion,
            registrado_por=principal.empleado_id,
        )
    )


@router.get("/incidentes-seguridad-pago/conteo", response_model=ConteoIncidentesSeguridadOut)
async def conteo_incidentes_seguridad(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ve_incidente_seguridad)],
    desde: date | None = None,
    hasta: date | None = None,
) -> ConteoIncidentesSeguridadOut:
    return ConteoIncidentesSeguridadOut(**await svc.contar_incidentes_seguridad(desde, hasta))


@router.get("/incidentes-seguridad-pago", response_model=list[IncidenteSeguridadOut])
async def listar_incidentes_seguridad(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ve_incidente_seguridad)],
    estado: str | None = None,
) -> list[IncidenteSeguridadOut]:
    return [
        IncidenteSeguridadOut.model_validate(i)
        for i in await svc.listar_incidentes_seguridad(estado)
    ]


@router.patch(
    "/incidentes-seguridad-pago/{incidente_seguridad_id}/transicionar",
    response_model=IncidenteSeguridadOut,
)
async def transicionar_incidente_seguridad(
    incidente_seguridad_id: int,
    data: TransicionarIncidenteSeguridadIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_transiciona_incidente_seguridad)],
) -> IncidenteSeguridadOut:
    return IncidenteSeguridadOut.model_validate(
        await svc.transicionar_incidente_seguridad(
            incidente_seguridad_id,
            estado_nuevo=data.estado_nuevo,
            empleado_id=principal.empleado_id,
        )
    )


# ========================================= política de seguridad de pagos (007, FR-012 a FR-014)
@router.get("/politica-seguridad-pagos", response_model=PoliticaSeguridadPagosOut)
async def politica_seguridad_pagos(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve_politica)]
) -> PoliticaSeguridadPagosOut:
    return PoliticaSeguridadPagosOut.model_validate(await svc.politica_seguridad_vigente())


@router.put(
    "/politica-seguridad-pagos",
    status_code=status.HTTP_201_CREATED,
    response_model=PoliticaSeguridadPagosOut,
)
async def definir_politica_seguridad(
    data: DefinirPoliticaIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_define_politica)],
) -> PoliticaSeguridadPagosOut:
    return PoliticaSeguridadPagosOut.model_validate(
        await svc.definir_politica_seguridad(texto=data.texto, definido_por=principal.empleado_id)
    )


@router.get(
    "/politica-seguridad-pagos/historial", response_model=list[PoliticaSeguridadPagosOut]
)
async def politica_seguridad_historial(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ve_politica)]
) -> list[PoliticaSeguridadPagosOut]:
    """FR-014 — historial de versiones (append-only) para saber cuál regía."""
    return [
        PoliticaSeguridadPagosOut.model_validate(p)
        for p in await svc.historial_politica_seguridad()
    ]


@router.get("/politica-seguridad-pagos/{politica_id}", response_model=PoliticaSeguridadPagosOut)
async def politica_seguridad_por_id(
    politica_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ve_politica)]
) -> PoliticaSeguridadPagosOut:
    return PoliticaSeguridadPagosOut.model_validate(
        await svc.politica_seguridad_por_id(politica_id)
    )


# ==================================================== forzar corrida (dev only)
if settings.app_env != "production":

    @router.post("/datafonos/evaluar-conformidad")
    async def forzar_evaluacion_conformidad(
        svc: ServiceDep, _: Annotated[Principal, Depends(_edita_datafonos)]
    ) -> dict:
        return {"datafonos_no_conformes": await svc.evaluar_conformidad_datafonos()}
