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
