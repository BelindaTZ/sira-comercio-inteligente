"""Esquemas Pydantic del módulo Compras — `contracts/compras.md` (US3)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

FrecuenciaReposicion = Literal["semanal", "mensual", "trimestral"]
TipoOrden = Literal["programada", "especial"]


# --- proveedores ---
class ProveedorIn(BaseModel):
    nombre: str
    ruc: str | None = None
    contacto: str | None = None
    telefono: str | None = None
    condiciones_pago: str | None = None
    frecuencia_reposicion: FrecuenciaReposicion | None = None


class ProveedorPatch(BaseModel):
    nombre: str | None = None
    ruc: str | None = None
    contacto: str | None = None
    telefono: str | None = None
    condiciones_pago: str | None = None
    frecuencia_reposicion: FrecuenciaReposicion | None = None


class ProveedorOut(BaseModel):
    proveedor_id: int
    nombre: str
    ruc: str | None
    contacto: str | None
    telefono: str | None
    condiciones_pago: str | None
    frecuencia_reposicion: str | None
    activo: bool

    model_config = {"from_attributes": True}


# --- órdenes ---
class LineaOrdenIn(BaseModel):
    product_id: int
    cantidad: int = Field(gt=0)
    costo_unitario: Decimal = Field(ge=0)


class OrdenIn(BaseModel):
    proveedor_id: int
    tienda_id: int
    empleado_id: int
    tipo: TipoOrden = "programada"
    lineas: list[LineaOrdenIn] = Field(min_length=1)
    motivo_desviacion: str | None = None


class PedidoEspecialIn(BaseModel):
    motivo: str = Field(min_length=1)


class OrdenLineaOut(BaseModel):
    product_id: int
    cantidad: int
    costo_unitario: Decimal


class OrdenOut(BaseModel):
    orden_id: int
    proveedor_id: int
    tienda_id: int
    empleado_id: int
    estado: str
    tipo: str
    fecha: date
    motivo_desviacion: str | None
    lineas: list[OrdenLineaOut] = []


class SugerenciaLinea(BaseModel):
    product_id: int
    tienda_id: int
    proveedor_id: int | None
    cantidad_disponible: int
    punto_reposicion: int
    cantidad_sugerida: int


# --- facturas y pagos ---
class FacturaIn(BaseModel):
    orden_id: int
    numero_factura: str
    monto_total: Decimal = Field(gt=0)
    fecha_emision: date
    fecha_vencimiento: date
    empleado_registra_id: int

    @model_validator(mode="after")
    def _vencimiento_valido(self) -> FacturaIn:
        if self.fecha_vencimiento < self.fecha_emision:
            raise ValueError("fecha_vencimiento no puede ser anterior a fecha_emision")
        return self


class FacturaOut(BaseModel):
    factura_id: int
    orden_id: int
    numero_factura: str
    monto_total: Decimal
    fecha_emision: date
    fecha_vencimiento: date
    estado: str
    empleado_registra_id: int
    pagado: Decimal = Decimal("0.00")
    saldo: Decimal = Decimal("0.00")


class PagoIn(BaseModel):
    monto: Decimal = Field(gt=0)
    medio_pago_id: int
    referencia: str | None = None
    empleado_registra_id: int
    empleado_autoriza_id: int


class PagoOut(BaseModel):
    pago_id: int
    factura_id: int
    monto: Decimal
    medio_pago_id: int
    referencia: str | None
    empleado_registra_id: int
    empleado_autoriza_id: int
    fecha_hora: datetime
    factura_estado: str


class ResumenCuentasPorPagar(BaseModel):
    desde: date
    hasta: date
    total_por_pagar: Decimal
    facturas_abiertas: int


class ReporteAutomaticoManual(BaseModel):
    mes: str
    total: int
    programadas: int
    especiales: int
    pct_programadas: float


class ProductoDeProveedor(BaseModel):
    product_id: int
    nombre: str | None = None
    product_category: str | None = None
    ordenes: int
    cantidad_total: int
    ultima_fecha: date | None


class ProveedorDeProducto(BaseModel):
    proveedor_id: int
    nombre: str | None = None
    ruc: str | None = None
    ordenes: int
    cantidad_total: int
    ultima_fecha: date | None
