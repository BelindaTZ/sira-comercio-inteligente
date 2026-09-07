"""Esquemas Pydantic del módulo Promociones — `contracts/promociones.md` (feature 005)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class ReglaAfinidadOut(BaseModel):
    regla_id: int
    product_id_antecedente: int
    product_id_consecuente: int
    soporte: Decimal
    confianza: Decimal
    lift: Decimal | None
    estado: str
    fecha_calculo: datetime

    model_config = {"from_attributes": True}


class DesactivarReglaIn(BaseModel):
    motivo: str | None = Field(default=None, max_length=300)


class RecomendacionOut(BaseModel):
    recomendacion_disponible: bool
    product_id_recomendado: int | None = None
    confianza: Decimal | None = None


class CuponAfinidadOut(BaseModel):
    envio_id: int
    household_id: int
    product_id_ofrecido: int | None
    regla_afinidad_id: int
    fecha_envio: datetime
    entregado: bool
    redimido: bool


class TasaRedencionAfinidadOut(BaseModel):
    enviados: int
    redimidos: int
    tasa_pct: float


class CambioAbcOut(BaseModel):
    product_id: int
    clasificacion_anterior: str | None
    clasificacion_nueva: str
    fecha_calculo: datetime

    model_config = {"from_attributes": True}


class ReglaLiquidacionOut(BaseModel):
    rotacion_minima_liquidacion_semanal: Decimal
    descuento_liquidacion_pct: Decimal


class ReglaLiquidacionPatch(BaseModel):
    rotacion_minima_liquidacion_semanal: Decimal | None = Field(default=None, ge=0)
    descuento_liquidacion_pct: Decimal | None = Field(default=None, ge=0, le=100)


class CandidatoLiquidacionOut(BaseModel):
    candidato_id: int
    product_id: int
    tienda_id: int
    semana: int
    anio: int
    rotacion_reciente_calculada: Decimal
    descuento_sugerido_pct: Decimal
    estado: str
    fecha_ejecucion: datetime | None = None
    ejecutado_por: int | None = None

    model_config = {"from_attributes": True}


class ColocacionIn(BaseModel):
    product_id: int
    tienda_id: int
    display_location: str | None = Field(default=None, max_length=2)
    mailer_location: str | None = Field(default=None, max_length=2)
    semana: int = Field(ge=1, le=53)
    anio: int = Field(ge=2000)

    @model_validator(mode="after")
    def _al_menos_una_ubicacion(self) -> ColocacionIn:
        if not self.display_location and not self.mailer_location:
            raise ValueError("Indica al menos display_location o mailer_location")
        return self


class ColocacionOut(BaseModel):
    promocion_id: int
    product_id: int
    tienda_id: int
    display_location: str | None
    mailer_location: str | None
    semana: int
    anio: int


class EfectoColocacionOut(BaseModel):
    ventas_semana_colocacion: int
    ventas_semana_referencia: int
