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
