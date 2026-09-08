"""Esquemas Pydantic del módulo RRHH.

CRUD base de empleado: `contracts/auth-administracion-sistema.md` (008).
Puestos críticos, retención, capacitación, clima laboral y plan de sucesión:
`specs/011-recursos-humanos/contracts/recursos-humanos.md`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class EmpleadoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    puesto_id: int
    tienda_id: int | None = None
    email: str | None = None
    telefono: str | None = Field(default=None, max_length=20)
    fecha_contratacion: date


class EmpleadoPatch(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    puesto_id: int | None = None
    tienda_id: int | None = None
    email: str | None = None
    telefono: str | None = Field(default=None, max_length=20)


class BajaEmpleadoIn(BaseModel):
    fecha_baja: date


class EmpleadoOut(BaseModel):
    empleado_id: int
    nombre: str
    puesto_id: int
    tienda_id: int | None
    email: str | None
    telefono: str | None
    fecha_contratacion: date
    fecha_baja: date | None
    activo: bool

    model_config = {"from_attributes": True}


# ============================================================ 011: puestos críticos
class MarcarCriticoIn(BaseModel):
    es_critico: bool


class PuestoOut(BaseModel):
    puesto_id: int
    nombre: str
    descripcion: str | None
    es_critico: bool

    model_config = {"from_attributes": True}


# ============================================================ 011: retención (FR-002)
class AccionRetencionIn(BaseModel):
    empleado_id: int
    fecha: date
    descripcion: str = Field(min_length=1)


class AccionRetencionOut(BaseModel):
    accion_id: int
    empleado_id: int
    fecha: date
    descripcion: str

    model_config = {"from_attributes": True}


# ============================================================ 011: capacitación (FR-003..FR-005)
class CapacitacionIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = None
    role_ids: list[int] = Field(min_length=1)


class CapacitacionOut(BaseModel):
    capacitacion_id: int
    nombre: str
    descripcion: str | None
    empleados_asignados: int


class CompletarCapacitacionIn(BaseModel):
    fecha_completado: date


class EmpleadoCapacitacionOut(BaseModel):
    empleado_id: int
    capacitacion_id: int
    fecha_completado: date | None

    model_config = {"from_attributes": True}


class CumplimientoCapacitacionItem(BaseModel):
    empleado_id: int
    nombre: str
    capacitacion_id: int
    nombre_capacitacion: str
    fecha_completado: date | None


# ================================================ 011: clima / rotación (FR-006, FR-007)
class ClimaLaboralIn(BaseModel):
    tienda_id: int
    periodo: str = Field(pattern=r"^\d{4}-S[12]$")
    resultado_promedio: Decimal = Field(ge=0, le=10)


class ClimaLaboralOut(BaseModel):
    encuesta_id: int
    tienda_id: int | None
    periodo: str
    resultado_promedio: Decimal | None
    fecha: date

    model_config = {"from_attributes": True}


class ClimaRotacionOut(BaseModel):
    encuesta_id: int
    resultado_promedio: Decimal | None
    tasa_rotacion_pct: float | None


# ================================================ 011: plan de sucesión (FR-008, FR-009)
class PlanSucesionIn(BaseModel):
    puesto_id: int
    empleado_candidato_id: int


class PlanSucesionOut(BaseModel):
    sucesion_id: int
    puesto_id: int
    empleado_candidato_id: int
    fecha: date

    model_config = {"from_attributes": True}


class CandidatoSucesion(BaseModel):
    empleado_candidato_id: int
    nombre: str
    fecha: date


class CoberturaSucesionItem(BaseModel):
    puesto_id: int
    nombre: str
    candidatos: list[CandidatoSucesion]
    sin_cobertura: bool
