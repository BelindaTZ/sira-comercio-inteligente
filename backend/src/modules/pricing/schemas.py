"""Esquemas Pydantic del módulo Pricing — `contracts/pricing.md` (feature 003)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

TipoCompetidor = Literal["supermercado", "tienda_barrio", "tienda_digital"]
FuenteCaptura = Literal["manual", "open_prices", "sintetico"]


# --- márgenes objetivo / regla de ajuste (FR-001, FR-004) ---
class MargenObjetivoOut(BaseModel):
    product_category: str
    margen_objetivo_pct: Decimal
    factor_sensibilidad: Decimal | None = None

    model_config = {"from_attributes": True}


class MargenObjetivoPatch(BaseModel):
    margen_objetivo_pct: Decimal | None = Field(default=None, ge=0, le=100)
    factor_sensibilidad: Decimal | None = Field(default=None, ge=0, le=1)


# --- margen objetivo efectivo ancla/nicho (FR-007) ---
class MargenEfectivoOut(BaseModel):
    product_id: int
    product_category: str | None
    es_ancla: bool
    margen_objetivo_categoria: Decimal | None
    modificador_pp: Decimal
    margen_objetivo_efectivo: Decimal
    margen_minimo_global_aplicado: bool


# --- propuestas de ajuste de precio (FR-005, FR-006) ---
class PropuestaOut(BaseModel):
    propuesta_id: int
    product_id: int
    precio_actual: Decimal
    precio_propuesto: Decimal
    margen_esperado_pct: Decimal
    estado: str
    fecha_generada: datetime
    fecha_resolucion: datetime | None = None
    aprobado_por: int | None = None

    model_config = {"from_attributes": True}


class RechazoIn(BaseModel):
    motivo: str | None = None


# --- revisión de margen bajo (FR-011, FR-012) ---
class MargenBajoOut(BaseModel):
    venta_detalle_id: int
    venta_id: int
    tienda_id: int
    product_id: int
    cantidad: int
    precio_aplicado: Decimal
    margen_real: Decimal | None
    fecha_venta: datetime
    motivo_descuento: str | None
    revisado: bool
    accion_correctiva: str | None = None


class RevisionIn(BaseModel):
    accion_correctiva: str = Field(min_length=1, max_length=500)


# --- reporte de margen (FR-003, FR-013) ---
class ReporteMargenFila(BaseModel):
    product_category: str
    margen_objetivo_pct: Decimal | None
    margen_real_pct: Decimal | None
    unidades_vendidas: int
    ingreso_total: Decimal
    costo_total: Decimal


class ReporteMargenOut(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    filas: list[ReporteMargenFila]


# --- competencia (FR-014, FR-015, FR-016) ---
class CompetidorIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    tipo: TipoCompetidor
    ciudad: str | None = Field(default=None, max_length=100)


class CompetidorOut(BaseModel):
    competidor_id: int
    nombre: str
    tipo: str
    ciudad: str | None

    model_config = {"from_attributes": True}


class PrecioCompetenciaIn(BaseModel):
    competidor_id: int
    precio: Decimal = Field(ge=0)
    fecha_captura: date | None = None
    tienda_id: int | None = None
    es_promocional: bool = False


class PrecioCompetenciaOut(BaseModel):
    precio_competencia_id: int
    product_id: int
    competidor_id: int | None
    tienda_id: int | None
    precio: Decimal
    fecha_captura: date
    es_promocional: bool
    fuente_captura: str
    registrado_por: int | None

    model_config = {"from_attributes": True}


class AlertaCompetenciaOut(BaseModel):
    product_id: int
    product_category: str | None
    precio_base: Decimal
    precio_competencia: Decimal
    fuente_captura: str
    fecha_captura: date
    desviacion_pct: Decimal


# --- configuración (FR-004, FR-007, FR-016) ---
class ConfiguracionOut(BaseModel):
    clave: str
    valor: Decimal
    descripcion: str | None

    model_config = {"from_attributes": True}


class ConfiguracionPatch(BaseModel):
    valor: Decimal = Field(ge=0)
