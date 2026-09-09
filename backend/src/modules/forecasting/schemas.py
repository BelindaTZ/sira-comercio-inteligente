"""Esquemas Pydantic del módulo Forecasting — `contracts/pronostico.md` (feature 004)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ModeloOut(BaseModel):
    modelo_id: int
    fecha_entrenamiento: datetime
    metrica_precision_validacion: Decimal | None
    estado: str
    fecha_resolucion: datetime | None = None
    aprobado_por: int | None = None
    observaciones: str | None = None

    model_config = {"from_attributes": True}


class ModeloDetalleOut(ModeloOut):
    productos_cubiertos: int = 0


class DecisionModeloIn(BaseModel):
    observaciones: str | None = Field(default=None, max_length=500)


class RechazoModeloIn(BaseModel):
    observaciones: str = Field(min_length=1, max_length=500)


class PronosticoOut(BaseModel):
    pronostico_disponible: bool
    cantidad_pronosticada: Decimal | None = None
    modelo_id: int | None = None
    semana: int | None = None
    anio: int | None = None


class MonitoreoOut(BaseModel):
    semana: int
    anio: int
    metrica_precision: Decimal
    supero_umbral_alerta: bool
    fecha_calculo: datetime

    model_config = {"from_attributes": True}


class AlertaMonitoreoOut(BaseModel):
    modelo_id: int
    semana: int
    anio: int
    metrica_precision: Decimal


class DemandaPerdidaFila(BaseModel):
    tienda_id: int
    product_category: str
    cantidad_eventos: int
    demanda_estimada_no_satisfecha: int


class DemandaPerdidaProducto(BaseModel):
    product_id: int
    producto_nombre: str | None = None
    product_category: str
    tienda_id: int
    cantidad_eventos: int
    demanda_estimada_no_satisfecha: int
    alta_demanda: bool = False
    ultimo_evento: datetime | None = None


class ConfiguracionOut(BaseModel):
    clave: str
    valor: Decimal
    descripcion: str | None

    model_config = {"from_attributes": True}


class ConfiguracionPatch(BaseModel):
    valor: Decimal = Field(ge=0)
