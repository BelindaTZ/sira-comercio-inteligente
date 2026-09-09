"""Esquemas Pydantic del módulo Catálogo — `contracts/catalogo.md` (US4)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Clasificacion = Literal["ancla", "nicho"]


class ProductoIn(BaseModel):
    codigo_barras: str = Field(min_length=1)
    nombre: str | None = None
    categoria: str | None = None
    marca: str | None = None
    costo: Decimal = Field(ge=0)
    precio_base: Decimal = Field(ge=0)
    es_perecedero: bool = False
    vida_util_dias: int | None = Field(default=None, gt=0)
    clasificacion: Clasificacion  # obligatoria al alta (FR-012)


class ProductoPatch(BaseModel):
    nombre: str | None = None
    categoria: str | None = None
    marca: str | None = None
    costo: Decimal | None = Field(default=None, ge=0)
    precio_base: Decimal | None = Field(default=None, ge=0)
    es_perecedero: bool | None = None
    vida_util_dias: int | None = Field(default=None, gt=0)
    clasificacion: Clasificacion | None = None
    imagen_url: str | None = Field(default=None, max_length=500)


class ProductoOut(BaseModel):
    product_id: int
    codigo_barras: str | None
    nombre: str | None
    marca: str | None
    product_category: str | None
    costo: Decimal | None
    precio_base: Decimal | None
    es_perecedero: bool
    vida_util_dias: int | None
    es_ancla: bool
    clasificacion_abc: str | None
    imagen_url: str | None
    activo: bool
    autocompletado: bool = False
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# --- gestión de precios y márgenes (US4) ---
EstadoMargen = Literal["optimo", "ajustado", "bajo", "sin_precio"]


class PrecioMatrizItem(BaseModel):
    product_id: int
    codigo_barras: str | None
    nombre: str | None
    marca: str | None
    product_category: str | None
    package_size: str | None
    imagen_url: str | None
    clasificacion_abc: str | None
    es_ancla: bool
    activo: bool
    costo: Decimal | None
    precio_base: Decimal | None
    precio_neto: Decimal | None = None
    iva_monto: Decimal | None = None
    iva_porcentaje: Decimal = Decimal("15.00")
    margen_pct: float | None
    margen_objetivo_pct: Decimal | None
    estado_margen: EstadoMargen


class CatalogoResumenOut(BaseModel):
    total_activos: int
    nuevos_30d: int
    con_ean: int
    total: int
    skus_con_elasticidad: int
    promos_vigentes: int
    skus_bajo_margen: int
    margen_bruto_ponderado_pct: float | None
    calculado_at: datetime | None = None


class SimulacionPrecioIn(BaseModel):
    delta_pct: Decimal = Field(ge=-30, le=30)


class SimulacionPrecioOut(BaseModel):
    product_id: int
    nombre: str | None
    pvp_actual: Decimal
    pvp_nuevo: Decimal
    margen_actual_pct: float | None
    margen_nuevo_pct: float | None
    unidades_mes: float
    factor_elasticidad: float
    delta_unidades_mes: float
    ganancia_mensual_delta: float
    es_inelastico: bool
