"""Esquemas Pydantic del módulo Inventario — `contracts/inventario.md` (US2)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

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
    motivo: str | None = Field(default=None, max_length=30)
    observaciones: str | None = Field(default=None, max_length=250)


class MermaIn(BaseModel):
    product_id: int
    tienda_id: int
    cantidad: int = Field(gt=0)
    causa: CausaMerma
    empleado_id: int
    lote_id: int | None = None
    destino: str | None = Field(default=None, max_length=30)
    observaciones: str | None = Field(default=None, max_length=250)


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
    capacidad_gondola: int | None = Field(default=None, gt=0)
    stock_minimo_reorden: int | None = Field(default=None, ge=0)
    dias_cobertura: int | None = Field(default=None, ge=1, le=60)
    politica_sobrestock: Literal["estricto", "autorizado"] | None = None


class VerificacionAnaquelIn(BaseModel):
    product_id: int
    tienda_id: int
    disponible: bool
    empleado_id: int
    fecha: date | None = None
    facing_asignado: int | None = Field(default=None, ge=0)
    facing_real: int | None = Field(default=None, ge=0)
    esl_ok: bool | None = None
    fifo_ok: bool | None = None
    observaciones: str | None = Field(default=None, max_length=300)


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


class UbicacionIn(BaseModel):
    product_id: int
    tienda_id: int
    pasillo: str = Field(min_length=1, max_length=40)
    gondola: str | None = Field(default=None, max_length=20)
    nivel: str | None = Field(default=None, max_length=20)
    empleado_id: int


class SolicitudReposicionIn(BaseModel):
    product_id: int
    tienda_id: int
    empleado_id: int


class SolicitudReposicionOut(BaseModel):
    alerta_id: int | None
    ya_existia: bool
    notificado: bool


class StockItemOut(BaseModel):
    """Una fila de la vista de stock por SKU (pantalla de Inventario)."""

    product_id: int
    nombre: str | None
    marca: str | None
    product_category: str | None
    clasificacion_abc: str | None
    imagen_url: str | None
    codigo_barras: str | None
    costo: Decimal | None
    precio_base: Decimal | None
    margen_pct: float | None
    es_perecedero: bool
    cantidad_disponible: int
    cantidad_minima: int
    cantidad_maxima: int | None
    en_transito: int = 0
    pasillo: str | None
    gondola: str | None
    lote_urgente: str | None
    fecha_vencimiento: date | None
    dias_para_vencer: int | None
    estado: Literal["quiebre", "vencido", "por_vencer", "sobre_stock", "normal"]


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


class MermaDetalleOut(MermaOut):
    fecha: date | None = None
    destino: str | None = None
    observaciones: str | None = None
    product_nombre: str | None = None
    product_sku: str | None = None
    product_categoria: str | None = None
    costo_unitario: Decimal | None = None
    imagen_url: str | None = None
    lote_numero: str | None = None
    lote_vencimiento: date | None = None
    empleado_nombre: str | None = None
    ubicacion_sala: str | None = None


class MermasKpisOut(BaseModel):
    merma_acumulada_mes: Decimal = Decimal("0")
    tasa_merma_pct: Decimal = Decimal("0")
    skus_criticos_count: int = 0
    tasa_recuperacion_pct: Decimal = Decimal("41.5")
    recuperacion_monto: Decimal = Decimal("0")
    pendientes_count: int = 0
    causas_desglose: dict[str, dict[str, Any]] = Field(default_factory=dict)


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
    capacidad_gondola: int | None = None
    stock_minimo_reorden: int | None = None
    dias_cobertura: int | None = None
    politica_sobrestock: str | None = None

    model_config = {"from_attributes": True}


class VerificacionAnaquelOut(BaseModel):
    id: int
    product_id: int
    tienda_id: int
    fecha: date
    disponible: bool
    empleado_id: int
    facing_asignado: int | None = None
    facing_real: int | None = None
    esl_ok: bool | None = None
    fifo_ok: bool | None = None
    observaciones: str | None = None

    model_config = {"from_attributes": True}
