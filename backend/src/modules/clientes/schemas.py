"""Esquemas Pydantic del módulo Clientes — `contracts/clientes.md` (feature 002)."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

# Validación ligera de formato de email — sin la dependencia `email-validator`
# (Principio VIII); la unicidad la resuelve la BD.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class DatosDemograficosIn(BaseModel):
    age: str | None = None
    income: str | None = None
    home_ownership: str | None = None
    marital_status: str | None = None
    household_size: str | None = None
    household_comp: str | None = None
    kids_count: str | None = None


class ClienteIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    email: str = Field(max_length=150)
    telefono: str | None = None
    documento_identidad: str | None = Field(default=None, max_length=13)
    fecha_nacimiento: date | None = None
    # Se captura obligatoriamente en el alta (FR-001) — sin default de aplicación.
    consentimiento_datos: bool
    datos_demograficos: DatosDemograficosIn | None = None

    @field_validator("email")
    @classmethod
    def _email_valido(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("email con formato inválido")
        return v.lower()


class ClientePatch(BaseModel):
    nombre: str | None = Field(default=None, max_length=150)
    email: str | None = Field(default=None, max_length=150)
    telefono: str | None = None
    documento_identidad: str | None = Field(default=None, max_length=13)
    fecha_nacimiento: date | None = None
    consentimiento_datos: bool | None = None
    datos_demograficos: DatosDemograficosIn | None = None

    @field_validator("email")
    @classmethod
    def _email_valido(cls, v: str | None) -> str | None:
        if v is not None and not _EMAIL_RE.match(v):
            raise ValueError("email con formato inválido")
        return v.lower() if v else v


class DatosDemograficosOut(DatosDemograficosIn):
    pass


class ClienteOut(BaseModel):
    household_id: int
    nombre: str | None
    email: str | None
    telefono: str | None
    documento_identidad: str | None
    fecha_nacimiento: date | None
    fecha_registro: date
    activo: bool
    consentimiento_datos: bool
    fecha_consentimiento_datos: datetime
    # Enriquecido con el último cálculo (join contra cliente_clv / churn_score).
    clv_score: Decimal | None = None
    nivel_fidelizacion_id: int | None = None
    severidad_churn: str | None = None


class ClienteDetalleOut(ClienteOut):
    datos_demograficos: DatosDemograficosOut | None = None


# --- niveles de fidelización (US2) ---
class NivelFidelizacionOut(BaseModel):
    nivel_id: int
    nombre: str
    umbral_clv_min: Decimal

    model_config = {"from_attributes": True}


class NivelUmbralPatch(BaseModel):
    umbral_clv_min: Decimal = Field(ge=0)


# --- riesgo de fuga (US3) ---
class RiesgoFugaOut(BaseModel):
    """Cada fila trae `ciclo_compra_dias` y `dias_desde_ultima_compra` ya
    calculados — el Jefe de Marketing nunca los deriva a mano (SC-005, FR-011)."""

    household_id: int
    nombre: str | None
    documento_identidad: str | None
    score: Decimal
    severidad: str
    ciclo_compra_dias: int | None
    dias_desde_ultima_compra: int | None
    fecha_calculo: date


# --- campañas por hito (US4) ---
class RedencionIn(BaseModel):
    household_id: int
    campaign_id: int


class TasaRedencionOut(BaseModel):
    tipo_evento: str
    enviados: int
    redimidos: int
    tasa: float


class EventoClienteOut(BaseModel):
    evento_id: int
    tipo_evento: str
    fecha: date
    cupon_enviado: str | None = None
    entregado: bool | None = None
    redimido: bool = False


# --- campañas de reactivación (US5) ---
class CampanaMiembroIn(BaseModel):
    household_id: int
    grupo: str  # "tratado" | "control" — validado en el servicio


class CampanaReactivacionIn(BaseModel):
    categoria_sira: str = "reactivacion"
    start_date: date
    end_date: date
    miembros: list[CampanaMiembroIn] = Field(min_length=1)


class DecisionIn(BaseModel):
    decision: str  # "aprobada_escalar" | "descartada"


class CampanaResumenOut(BaseModel):
    campaign_id: int
    categoria_sira: str | None
    start_date: date
    end_date: date

    model_config = {"from_attributes": True}


class CampanaResultadoOut(BaseModel):
    tasa_retorno_tratado: Decimal | None
    tasa_retorno_control: Decimal | None
    uplift: Decimal | None
    decision: str | None
    fecha_calculo: date | None


class CampanaDetalleOut(BaseModel):
    campaign_id: int
    categoria_sira: str | None
    start_date: date
    end_date: date
    enviada: bool
    miembros: list[CampanaMiembroIn]
    resultado: CampanaResultadoOut | None = None
