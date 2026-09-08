"""Esquemas Pydantic del módulo Inventario — `contracts/inventario.md` (US2)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

CausaMerma = Literal["caducidad", "robo", "rotura", "error_humano"]
DecisionMerma = Literal["validada", "rechazada"]


# --- entrada ---
class RecepcionIn(BaseModel):
    orden_id: int
    product_id: int
    tienda_id: int
    cantidad: int = Field(gt=0)
    fecha_vencimiento: date | None = None
    codigo_lote_proveedor: str | None = None


class AjusteIn(BaseModel):
    product_id: int
    tienda_id: int
    cantidad_fisica: int = Field(ge=0)
    empleado_id: int


class MermaIn(BaseModel):
    product_id: int
    tienda_id: int
    cantidad: int = Field(gt=0)
    causa: CausaMerma
    empleado_id: int
    lote_id: int | None = None


class ValidarMermaIn(BaseModel):
    empleado_id: int
    decision: DecisionMerma


class AtenderAlertaIn(BaseModel):
    empleado_id: int


class QuiebreIn(BaseModel):
    product_id: int
    tienda_id: int
    empleado_id: int
    demanda_estimada_no_satisfecha: int | None = Field(default=None, gt=0)


class StockMaximoIn(BaseModel):
    product_category: str
    tienda_id: int
    cantidad_maxima: int = Field(gt=0)
    empleado_id: int


class VerificacionAnaquelIn(BaseModel):
    product_id: int
    tienda_id: int
    disponible: bool
    empleado_id: int
    fecha: date | None = None


# --- salida ---
class LoteOut(BaseModel):
    lote_id: int
    product_id: int
    producto_nombre: str | None = None
    tienda_id: int
    cantidad_recibida: int
    cantidad_disponible: int
    fecha_vencimiento: date | None
    codigo_lote_proveedor: str | None
    dias_para_vencer: int | None


class ProductoBusquedaOut(BaseModel):
    """Item de autocompletado para los formularios de operación."""

    product_id: int
    nombre: str | None
    marca: str | None
    product_category: str | None
    clasificacion_abc: str | None
    imagen_url: str | None

    model_config = {"from_attributes": True}


class RecepcionOut(BaseModel):
    recepcion_id: int
    lote_id: int
    orden_id: int
    product_id: int
    tienda_id: int
    cantidad: int
    fecha_vencimiento: date | None
    stock_disponible: int


class AjusteOut(BaseModel):
    ajuste_id: int
    product_id: int
    tienda_id: int
    cantidad_sistema: int
    cantidad_fisica: int
    diferencia: int
    stock_disponible: int


class MermaOut(BaseModel):
    merma_id: int
    product_id: int
    tienda_id: int
    lote_id: int | None
    cantidad: int
    causa: str
    valor: Decimal
    empleado_id: int
    estado_validacion: str
    empleado_valida_id: int | None
    fecha_validacion: datetime | None


class AlertaOut(BaseModel):
    alerta_id: int
    tipo: str
    product_id: int
    producto_nombre: str | None = None
    tienda_id: int
    lote_id: int | None
    estado: str
    fecha_generada: datetime
    fecha_atendida: datetime | None
    empleado_atiende_id: int | None
    # feature 004 (FR-010): 'modelo_pronostico' o 'rotacion_reciente'
    origen_calculo: str = "rotacion_reciente"

    model_config = {"from_attributes": True}


class QuiebreOut(BaseModel):
    evento_id: int
    product_id: int
    tienda_id: int
    empleado_id: int
    demanda_estimada_no_satisfecha: int | None
    es_alta_demanda: bool
    fecha_hora: datetime

    model_config = {"from_attributes": True}


class StockMaximoOut(BaseModel):
    id: int
    product_category: str
    tienda_id: int
    cantidad_maxima: int
    empleado_id: int
    fecha_definicion: datetime

    model_config = {"from_attributes": True}


class VerificacionAnaquelOut(BaseModel):
    id: int
    product_id: int
    tienda_id: int
    fecha: date
    disponible: bool
    empleado_id: int

    model_config = {"from_attributes": True}
