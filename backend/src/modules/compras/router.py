"""Router del módulo Compras — `contracts/compras.md` (US3, T060/T088).

RBAC: módulo `Operaciones` (órdenes, proveedores, sugerencias) y módulo `Finanzas`
(facturas y pagos a proveedor).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.security import Principal, require_permission
from src.modules.compras.repository import ComprasRepository
from src.modules.compras.schemas import (
    FacturaIn,
    FacturaOut,
    OrdenIn,
    OrdenLineaOut,
    OrdenOut,
    PagoIn,
    PagoOut,
    PedidoEspecialIn,
    ProductoDeProveedor,
    ProveedorDeProducto,
    ProveedorIn,
    ProveedorOut,
    ProveedorPatch,
    ReporteAutomaticoManual,
    ResumenCuentasPorPagar,
    SugerenciaLinea,
)
from src.modules.compras.service import ComprasService
from src.shared.exceptions import ForbiddenError, NotFoundError
from src.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/compras", tags=["compras"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ver_ops = require_permission("Operaciones", "ordenes_compra", "select")
_ordenes = require_permission("Operaciones", "ordenes_compra", "insert")
_ordenes_aprob = require_permission("Operaciones", "ordenes_compra", "update")
_proveedores = require_permission("Operaciones", "proveedores", "insert")
_proveedores_upd = require_permission("Operaciones", "proveedores", "update")
_factura_ver = require_permission("Finanzas", "facturas_proveedor", "select")
_factura = require_permission("Finanzas", "facturas_proveedor", "insert")
_pago = require_permission("Finanzas", "pagos_proveedor", "insert")


def _svc(session: SessionDep) -> ComprasService:
    return ComprasService(ComprasRepository(session))


ServiceDep = Annotated[ComprasService, Depends(_svc)]


async def _orden_out(svc: ComprasService, orden) -> OrdenOut:
    lineas = await svc.repo.lineas_de_orden(orden.orden_id)
    prov = await svc.repo.get_proveedor(orden.proveedor_id)
    lineas_out = []
    total_neto = Decimal("0.00")
    total_unidades = 0
    for ln in lineas:
        prod = await svc.repo.get_producto(ln.product_id)
        prod_nombre = prod.nombre if prod else None
        total_neto += Decimal(str(ln.cantidad)) * ln.costo_unitario
        total_unidades += ln.cantidad
        lineas_out.append(
            OrdenLineaOut(
                product_id=ln.product_id,
                product_nombre=prod_nombre,
                cantidad=ln.cantidad,
                costo_unitario=ln.costo_unitario,
            )
        )
    return OrdenOut(
        orden_id=orden.orden_id,
        proveedor_id=orden.proveedor_id,
        proveedor_nombre=prov.nombre if prov else None,
        tienda_id=orden.tienda_id,
        empleado_id=orden.empleado_id,
        estado=orden.estado,
        tipo=orden.tipo,
        fecha=orden.fecha,
        motivo_desviacion=orden.motivo_desviacion,
        total_neto=total_neto,
        cantidad_skus=len(lineas),
        total_unidades=total_unidades,
        lineas=lineas_out,
    )


async def _factura_out(svc: ComprasService, factura) -> FacturaOut:
    pagado = await svc.repo.pagado_de_factura(factura.factura_id)
    return FacturaOut(
        factura_id=factura.factura_id,
        orden_id=factura.orden_id,
        numero_factura=factura.numero_factura,
        monto_total=factura.monto_total,
        fecha_emision=factura.fecha_emision,
        fecha_vencimiento=factura.fecha_vencimiento,
        estado=factura.estado,
        empleado_registra_id=factura.empleado_registra_id,
        pagado=pagado,
        saldo=factura.monto_total - pagado,
    )


# ---------------------------------------------------------------- sugerencias
@router.get("/sugerencias", response_model=list[SugerenciaLinea])
async def sugerencias(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_ops)],
    tienda_id: int = Query(...),
) -> list[SugerenciaLinea]:
    return [SugerenciaLinea(**s) for s in await svc.generar_sugerencia_semanal(tienda_id)]


# ------------------------------------------------------------------- proveedores
@router.post("/proveedores", status_code=status.HTTP_201_CREATED, response_model=ProveedorOut)
async def crear_proveedor(
    data: ProveedorIn, svc: ServiceDep, _: Annotated[Principal, Depends(_proveedores)]
) -> ProveedorOut:
    return ProveedorOut.model_validate(await svc.crear_proveedor(data))


@router.patch("/proveedores/{proveedor_id}", response_model=ProveedorOut)
async def actualizar_proveedor(
    proveedor_id: int,
    data: ProveedorPatch,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_proveedores_upd)],
) -> ProveedorOut:
    return ProveedorOut.model_validate(await svc.actualizar_proveedor(proveedor_id, data))


# --- historial proveedor↔producto (Ronda 11, FR-044) — sólo lectura ---
@router.get("/proveedores/{proveedor_id}/productos", response_model=list[ProductoDeProveedor])
async def productos_de_proveedor(
    proveedor_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver_ops)]
) -> list[ProductoDeProveedor]:
    return [ProductoDeProveedor(**r) for r in await svc.productos_de_proveedor(proveedor_id)]


@router.get("/productos/{product_id}/proveedores", response_model=list[ProveedorDeProducto])
async def proveedores_de_producto(
    product_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver_ops)]
) -> list[ProveedorDeProducto]:
    return [ProveedorDeProducto(**r) for r in await svc.proveedores_de_producto(product_id)]


# ------------------------------------------------------------------- órdenes
@router.get("/ordenes", response_model=list[OrdenOut])
async def listar_ordenes(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_ops)],
    tienda_id: int | None = Query(None),
    estado: str | None = Query(None),
) -> list[OrdenOut]:
    ordenes = await svc.listar_ordenes(tienda_id=tienda_id, estado=estado)
    return [await _orden_out(svc, o) for o in ordenes]


@router.get("/ordenes/{orden_id}", response_model=OrdenOut)
async def orden_por_id(
    orden_id: int,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_ops)],
) -> OrdenOut:
    orden = await svc.repo.get_orden_for_update(orden_id)
    if not orden:
        raise NotFoundError(f"Orden de compra {orden_id} no existe")
    return await _orden_out(svc, orden)


@router.post("/ordenes", status_code=status.HTTP_201_CREATED, response_model=OrdenOut)
async def crear_orden(
    data: OrdenIn, svc: ServiceDep, _: Annotated[Principal, Depends(_ordenes)]
) -> OrdenOut:
    return await _orden_out(svc, await svc.crear_orden(data))


@router.post("/ordenes/{orden_id}/aprobar", response_model=OrdenOut)
async def aprobar_orden(
    orden_id: int,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_ordenes_aprob)],
) -> OrdenOut:
    return await _orden_out(svc, await svc.aprobar_orden(orden_id, principal.empleado_id))


@router.post("/ordenes/{orden_id}/pedido-especial", response_model=OrdenOut)
async def pedido_especial(
    orden_id: int,
    data: PedidoEspecialIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ordenes_aprob)],
) -> OrdenOut:
    return await _orden_out(svc, await svc.pedido_especial(orden_id, data.motivo))


# ------------------------------------------------------------------- facturas
@router.post("/facturas", status_code=status.HTTP_201_CREATED, response_model=FacturaOut)
async def registrar_factura(
    data: FacturaIn, svc: ServiceDep, _: Annotated[Principal, Depends(_factura)]
) -> FacturaOut:
    return await _factura_out(svc, await svc.registrar_factura(data))


@router.get("/facturas", response_model=Page[FacturaOut])
async def listar_facturas(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_factura_ver)],
    params: Annotated[PageParams, Depends(page_params)],
    estado: str | None = None,
    vencimiento_antes: date | None = None,
) -> Page[FacturaOut]:
    from src.models.factura_proveedor import FacturaProveedor

    stmt = svc.repo.facturas_query(estado=estado, vencimiento_antes=vencimiento_antes)
    page = await svc.repo.paginate(
        params, stmt=stmt, order_by=FacturaProveedor.fecha_vencimiento.asc()
    )
    items = [await _factura_out(svc, f) for f in page.items]
    return Page(items=items, total=page.total, page=page.page, size=page.size)


@router.get("/facturas/resumen", response_model=ResumenCuentasPorPagar)
async def resumen_cuentas_por_pagar(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_factura_ver)],
    desde: date = Query(...),
    hasta: date = Query(...),
) -> ResumenCuentasPorPagar:
    return ResumenCuentasPorPagar(**await svc.resumen_cuentas_por_pagar(desde, hasta))


@router.get("/reportes/automatico-vs-manual", response_model=ReporteAutomaticoManual)
async def reporte_automatico_vs_manual(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_ops)],
    mes: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
) -> ReporteAutomaticoManual:
    return ReporteAutomaticoManual(**await svc.reporte_automatico_vs_manual(mes))


@router.post("/facturas/{factura_id}/pagos", response_model=PagoOut)
async def registrar_pago(
    factura_id: int,
    data: PagoIn,
    svc: ServiceDep,
    principal: Annotated[Principal, Depends(_pago)],
) -> PagoOut:
    # T073 / checklists/security.md: control de doble persona también entre
    # requests separados. El paso de autorización lo ejecuta (y firma su JWT)
    # el propio autorizador, que además no puede ser quien registró el pago.
    if data.empleado_autoriza_id != principal.empleado_id:
        raise ForbiddenError("El pago debe autorizarlo el empleado autenticado")
    if data.empleado_registra_id == principal.empleado_id:
        raise ForbiddenError("Quien autoriza no puede ser quien registró el pago")

    pago = await svc.registrar_pago(factura_id, data)
    factura = await svc.repo.get_factura_for_update(factura_id)
    return PagoOut(
        pago_id=pago.pago_id,
        factura_id=pago.factura_id,
        monto=pago.monto,
        medio_pago_id=pago.medio_pago_id,
        referencia=pago.referencia,
        empleado_registra_id=pago.empleado_registra_id,
        empleado_autoriza_id=pago.empleado_autoriza_id,
        fecha_hora=pago.fecha_hora,
        factura_estado=factura.estado,
    )
