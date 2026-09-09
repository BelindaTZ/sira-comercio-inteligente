"""Esquemas Pydantic del módulo Ventas — contrato de `contracts/ventas.md`."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

TipoComprobante = Literal["factura", "nota_venta"]
ResultadoPagoTarjeta = Literal["aprobado", "rechazado", "error_tecnico"]
EscenarioTarjeta = Literal["aprobado", "rechazado", "error_tecnico"]


# --- entrada ---
class IniciarVentaIn(BaseModel):
    tienda_id: int
    cajero_id: int
    household_id: int | None = None


class AgregarLineaIn(BaseModel):
    product_id: int | None = None
    codigo_barras: str | None = None
    cantidad: int = Field(gt=0)

    @model_validator(mode="after")
    def _uno_u_otro(self) -> AgregarLineaIn:
        if (self.product_id is None) == (self.codigo_barras is None):
            raise ValueError("Indica product_id o codigo_barras (exactamente uno)")
        return self


class RemoverLineaIn(BaseModel):
    autoriza_empleado_id: int
    motivo: str | None = None


class DescuentoManualIn(BaseModel):
    """FR-009 — descuento manual con autorización obligatoria de un
    Encargado_Tienda (o superior) distinto del cajero, sin excepción por monto."""

    tipo: Literal["monto", "porcentaje"]
    valor: Decimal = Field(gt=0)
    motivo: str = Field(min_length=1, max_length=200)
    empleado_aplica_id: int
    empleado_autoriza_id: int


class PagoTarjetaIn(BaseModel):
    monto: Decimal = Field(gt=0)
    # Afordancia de demo (modo test): elige qué tarjeta de prueba de Stripe usa el
    # backend. El cajero nunca envía datos de tarjeta reales (FR-003).
    escenario: EscenarioTarjeta = "aprobado"


class ConfirmarVentaIn(BaseModel):
    medio_pago_id: int
    tipo_comprobante: TipoComprobante = "nota_venta"
    identificacion_comprador: str | None = None
    razon_social_comprador: str | None = None

    @model_validator(mode="after")
    def _factura_requiere_identificacion(self) -> ConfirmarVentaIn:
        if self.tipo_comprobante == "factura" and not (self.identificacion_comprador or "").strip():
            raise ValueError("tipo_comprobante='factura' requiere identificacion_comprador")
        return self


class AnularVentaIn(BaseModel):
    empleado_id: int
    motivo: str = Field(min_length=1, max_length=200)


class DevolucionIn(BaseModel):
    product_id: int
    cantidad: int = Field(gt=0)
    motivo: str = Field(min_length=1, max_length=200)
    # None → el servicio lo decide según el motivo (FR-025). El caller puede forzarlo.
    reintegra_inventario: bool | None = None


class DevolucionOut(BaseModel):
    devolucion_id: int
    venta_id: int
    product_id: int
    cantidad: int
    motivo: str
    reintegra_inventario: bool
    empleado_id: int


# --- salida ---
class LineaOut(BaseModel):
    venta_detalle_id: int
    product_id: int
    cantidad: int
    sales_value: Decimal
    subtotal: Decimal
    # feature 003 — descuento manual / margen (None si no aplica)
    retail_disc: Decimal = Decimal("0")
    motivo_descuento: str | None = None
    empleado_autoriza_id: int | None = None
    margen_real: Decimal | None = None
    margen_bajo_minimo: bool = False


class VentaOut(BaseModel):
    venta_id: int
    tienda_id: int
    cajero_id: int
    household_id: int | None
    estado: str
    total: Decimal
    medio_pago_id: int | None
    tipo_comprobante: str
    identificacion_comprador: str
    razon_social_comprador: str
    fecha_hora: datetime
    comprobante_objeto: str | None = None
    lineas: list[LineaOut] = []


class PagoTarjetaOut(BaseModel):
    intento_id: int
    resultado: ResultadoPagoTarjeta
    referencia_pasarela: str | None


# --- feature 007: medios de pago, datáfono disponible, tiempo de cobro ---
class MedioPagoOut(BaseModel):
    medio_pago_id: int
    nombre: str
    aprobado: bool
    aprobado_por: int | None = None
    fecha_aprobacion: datetime | None = None
    fecha_baja: datetime | None = None

    model_config = {"from_attributes": True}


class MedioPagoDisponibleOut(BaseModel):
    medio_pago_id: int
    nombre: str

    model_config = {"from_attributes": True}


class AltaMedioPagoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=30)


class DatafonoDisponibleOut(BaseModel):
    disponible: bool
    estado: str | None


class CajaOut(BaseModel):
    caja_id: int
    tienda_id: int
    nombre: str
    activa: bool

    model_config = {"from_attributes": True}


class CatalogoPosItem(BaseModel):
    """Producto para el grid de registro rápido del POS."""

    product_id: int
    nombre: str | None
    marca: str | None
    product_category: str | None
    codigo_barras: str | None
    imagen_url: str | None
    precio_base: Decimal
    stock_disponible: int


class TiempoCobroSemanalOut(BaseModel):
    caja_id: int
    semana: int
    duracion_promedio_segundos: float | None
    cantidad_ventas_consideradas: int


class TiempoCobroMensualItem(BaseModel):
    tienda_id: int
    duracion_promedio_segundos: float | None
    cantidad_ventas_consideradas: int
