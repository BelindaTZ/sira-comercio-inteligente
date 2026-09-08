"""Router del módulo Ventas — implementa `contracts/ventas.md` (T031).

Sin lógica de negocio (Principio XI): cada endpoint valida RBAC, delega en
`VentasService` y forma la respuesta.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.security import Principal, require_permission
from src.integrations import reportlab_invoice
from src.models.venta import Venta
from src.modules.ventas.repository import VentasRepository
from src.modules.ventas.schemas import (
    AgregarLineaIn,
    AltaMedioPagoIn,
    AnularVentaIn,
    ConfirmarVentaIn,
    DatafonoDisponibleOut,
    DescuentoManualIn,
    DevolucionIn,
    DevolucionOut,
    IniciarVentaIn,
    LineaOut,
    MedioPagoDisponibleOut,
    MedioPagoOut,
    PagoTarjetaIn,
    PagoTarjetaOut,
    RemoverLineaIn,
    TiempoCobroMensualItem,
    TiempoCobroSemanalOut,
    VentaOut,
)
from src.modules.ventas.service import VentasService
from src.shared.exceptions import ForbiddenError, NotFoundError
from src.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/ventas", tags=["ventas"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ver = require_permission("Ventas", "ventas", "select")
_operar = require_permission("Ventas", "ventas", "insert")
_actualizar = require_permission("Ventas", "ventas", "update")
_linea_insert = require_permission("Ventas", "venta_detalle", "insert")
_linea_update = require_permission("Ventas", "venta_detalle", "update")
_linea_delete = require_permission("Ventas", "venta_detalle", "delete")
_devolucion = require_permission("Ventas", "devoluciones", "insert")
# feature 007 — Jefe_TI administra medios_pago; el resto son lecturas del módulo Ventas.
_admin_medios = require_permission("Ventas", "medios_pago", "select")
_alta_medio = require_permission("Ventas", "medios_pago", "insert")
_baja_medio = require_permission("Ventas", "medios_pago", "update")


def _svc(session: SessionDep) -> VentasService:
    return VentasService(VentasRepository(session))


ServiceDep = Annotated[VentasService, Depends(_svc)]


async def _venta_out(svc: VentasService, venta: Venta) -> VentaOut:
    lineas = await svc.repo.lineas_de(venta.venta_id)
    return VentaOut(
        venta_id=venta.venta_id,
        tienda_id=venta.tienda_id,
        cajero_id=venta.cajero_id,
        household_id=venta.household_id,
        estado=venta.estado,
        total=venta.total,
        medio_pago_id=venta.medio_pago_id,
        tipo_comprobante=venta.tipo_comprobante,
        identificacion_comprador=venta.identificacion_comprador,
        razon_social_comprador=venta.razon_social_comprador,
        fecha_hora=venta.fecha_hora,
        comprobante_objeto=venta.comprobante_objeto,
        lineas=[
            LineaOut(
                venta_detalle_id=ln.venta_detalle_id,
                product_id=ln.product_id,
                cantidad=ln.cantidad,
                sales_value=ln.sales_value,
                subtotal=ln.sales_value * ln.cantidad - (ln.retail_disc or 0),
                retail_disc=ln.retail_disc or 0,
                motivo_descuento=ln.motivo_descuento,
                empleado_autoriza_id=ln.empleado_autoriza_id,
                margen_real=ln.margen_real,
                margen_bajo_minimo=ln.margen_bajo_minimo,
            )
            for ln in lineas
        ],
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=VentaOut)
async def iniciar_venta(
    data: IniciarVentaIn, svc: ServiceDep, _: Annotated[Principal, Depends(_operar)]
) -> VentaOut:
    venta = await svc.iniciar_venta(data)
    return await _venta_out(svc, venta)


@router.post("/{venta_id}/lineas", response_model=VentaOut)
async def agregar_linea(
    venta_id: int,
    data: AgregarLineaIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_linea_insert)],
) -> VentaOut:
    venta, _linea = await svc.agregar_linea(venta_id, data)
    return await _venta_out(svc, venta)


@router.delete("/{venta_id}/lineas/{linea_id}", response_model=VentaOut)
async def remover_linea(
    venta_id: int,
    linea_id: int,
    data: RemoverLineaIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_linea_delete)],
) -> VentaOut:
    # El principal autenticado es quien autoriza: no se autoriza en nombre de otro.
    if data.autoriza_empleado_id != principal.empleado_id:
        raise ForbiddenError("autoriza_empleado_id debe coincidir con el empleado autenticado")
    venta = await svc.remover_linea(venta_id, linea_id, data)
    return await _venta_out(svc, venta)


@router.post("/{venta_id}/lineas/{linea_id}/descuento", response_model=VentaOut)
async def aplicar_descuento_manual(
    venta_id: int,
    linea_id: int,
    data: DescuentoManualIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_linea_update)],
) -> VentaOut:
    """FR-009/FR-010 — el cajero (autenticado) aplica; un Encargado_Tienda o
    superior distinto autoriza (`contracts/pricing.md`)."""
    if data.empleado_aplica_id != principal.empleado_id:
        raise ForbiddenError("empleado_aplica_id debe coincidir con el empleado autenticado")
    venta, _linea = await svc.aplicar_descuento_manual(venta_id, linea_id, data)
    return await _venta_out(svc, venta)


@router.post("/{venta_id}/pago-tarjeta", response_model=PagoTarjetaOut)
async def pago_tarjeta(
    venta_id: int,
    data: PagoTarjetaIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_actualizar)],
) -> PagoTarjetaOut:
    intento = await svc.procesar_pago_tarjeta(venta_id, data)
    return PagoTarjetaOut(
        intento_id=intento.intento_id,
        resultado=intento.resultado,
        referencia_pasarela=intento.referencia_pasarela,
    )


@router.post("/{venta_id}/confirmar", response_model=VentaOut)
async def confirmar_venta(
    venta_id: int,
    data: ConfirmarVentaIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_actualizar)],
) -> VentaOut:
    venta = await svc.confirmar_venta(venta_id, data)
    return await _venta_out(svc, venta)


@router.post("/{venta_id}/anular", response_model=VentaOut)
async def anular_venta(
    venta_id: int,
    data: AnularVentaIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_actualizar)],
) -> VentaOut:
    venta = await svc.anular_venta(venta_id, data)
    return await _venta_out(svc, venta)


@router.post(
    "/{venta_id}/devoluciones", status_code=status.HTTP_201_CREATED, response_model=DevolucionOut
)
async def registrar_devolucion(
    venta_id: int,
    data: DevolucionIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_devolucion)],
) -> DevolucionOut:
    dev = await svc.registrar_devolucion(venta_id, data, principal.empleado_id)
    return DevolucionOut(
        devolucion_id=dev.devolucion_id,
        venta_id=dev.venta_id,
        product_id=dev.product_id,
        cantidad=dev.cantidad,
        motivo=dev.motivo,
        reintegra_inventario=dev.reintegra_inventario,
        empleado_id=dev.empleado_id,
    )


@router.get("/{venta_id}/comprobante")
async def comprobante(
    venta_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver)]
) -> Response:
    venta = await svc.repo.get_venta(venta_id)
    if venta is None:
        raise NotFoundError(f"Venta {venta_id} no existe")
    if not venta.comprobante_objeto:
        raise NotFoundError("La venta aún no tiene comprobante emitido")
    pdf = reportlab_invoice.descargar_comprobante(venta.comprobante_objeto)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="venta-{venta_id}.pdf"'},
    )


# ==================================================== feature 007: pagos y seguridad
@router.get("/medios-pago/disponibles", response_model=list[MedioPagoDisponibleOut])
async def medios_pago_disponibles(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ver)]
) -> list[MedioPagoDisponibleOut]:
    """FR-007 — medios de pago ofrecidos en caja (aprobados y sin baja)."""
    return [MedioPagoDisponibleOut.model_validate(m) for m in await svc.medios_pago_disponibles()]


@router.get("/medios-pago", response_model=list[MedioPagoOut])
async def listar_medios_pago(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_admin_medios)],
    aprobado: bool | None = None,
) -> list[MedioPagoOut]:
    return [MedioPagoOut.model_validate(m) for m in await svc.listar_medios_pago(aprobado)]


@router.post("/medios-pago", status_code=status.HTTP_201_CREATED, response_model=MedioPagoOut)
async def alta_medio_pago(
    data: AltaMedioPagoIn, svc: ServiceDep, principal: Annotated[Principal, Depends(_alta_medio)]
) -> MedioPagoOut:
    return MedioPagoOut.model_validate(
        await svc.dar_alta_medio_pago(data.nombre, principal.empleado_id)
    )


@router.patch("/medios-pago/{medio_pago_id}/baja", response_model=MedioPagoOut)
async def baja_medio_pago(
    medio_pago_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_baja_medio)]
) -> MedioPagoOut:
    return MedioPagoOut.model_validate(await svc.dar_baja_medio_pago(medio_pago_id))


@router.get("/cajas/{caja_id}/datafono-disponible", response_model=DatafonoDisponibleOut)
async def datafono_disponible(
    caja_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver)]
) -> DatafonoDisponibleOut:
    """FR-004 — el flujo de cobro consulta esto antes de intentar con tarjeta."""
    return DatafonoDisponibleOut(**await svc.datafono_disponible_de_caja(caja_id))


_ROLES_REPORTE_COBRO_CAJA = frozenset(
    {"Encargado_Tienda", "Jefe_Comercial", "Jefe_Operaciones", "Gerente_General"}
)
_ROLES_REPORTE_COBRO_RED = frozenset({"Jefe_Comercial", "Gerente_General"})


@router.get("/cajas/{caja_id}/tiempo-cobro-semanal", response_model=TiempoCobroSemanalOut)
async def tiempo_cobro_semanal(
    caja_id: int,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_ver)],
    semana: int = Query(..., ge=1, le=53),
    anio: int | None = None,
) -> TiempoCobroSemanalOut:
    """FR-016 — revisión semanal por caja (Encargado de Tienda)."""
    if principal.rol not in _ROLES_REPORTE_COBRO_CAJA:
        raise ForbiddenError("Este reporte es para el Encargado de Tienda o superior")
    return TiempoCobroSemanalOut(**await svc.tiempo_cobro_semanal(caja_id, semana, anio))


@router.get("/tiendas/tiempo-cobro-mensual", response_model=list[TiempoCobroMensualItem])
async def tiempo_cobro_mensual(
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_ver)],
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2000),
) -> list[TiempoCobroMensualItem]:
    """FR-017 — revisión mensual por tienda a nivel de red (Jefe Comercial)."""
    if principal.rol not in _ROLES_REPORTE_COBRO_RED:
        raise ForbiddenError("El reporte de tiempo de cobro a nivel de red es del Jefe Comercial")
    return [TiempoCobroMensualItem(**f) for f in await svc.tiempo_cobro_mensual(mes, anio)]


@router.get("", response_model=Page[VentaOut])
async def listar_ventas(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver)],
    params: Annotated[PageParams, Depends(page_params)],
    tienda_id: int | None = None,
    estado: str | None = None,
    household_id: int | None = None,
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
) -> Page[VentaOut]:
    stmt = select(Venta)
    if tienda_id is not None:
        stmt = stmt.where(Venta.tienda_id == tienda_id)
    if estado is not None:
        stmt = stmt.where(Venta.estado == estado)
    if household_id is not None:
        stmt = stmt.where(Venta.household_id == household_id)
    if fecha_desde is not None:
        stmt = stmt.where(Venta.fecha_hora >= fecha_desde)
    if fecha_hasta is not None:
        stmt = stmt.where(Venta.fecha_hora < fecha_hasta)

    page = await svc.repo.paginate(params, stmt=stmt, order_by=Venta.fecha_hora.desc())
    items = [await _venta_out(svc, v) for v in page.items]
    return Page(items=items, total=page.total, page=page.page, size=page.size)
