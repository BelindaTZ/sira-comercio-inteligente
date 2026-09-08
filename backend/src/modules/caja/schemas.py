"""Esquemas Pydantic del módulo Caja — `contracts/caja-mermas-fraude.md` (feature 006)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ============================================================ apertura / cuadre (US1)
class AperturaIn(BaseModel):
    caja_id: int
    fondo_inicial: Decimal = Field(ge=0)


class AperturaOut(BaseModel):
    apertura_id: int
    caja_id: int
    cajero_id: int
    fondo_inicial: Decimal
    fecha_hora: datetime

    model_config = {"from_attributes": True}


class CierreIn(BaseModel):
    caja_id: int
    total_registrado: Decimal = Field(ge=0)


class CierreOut(BaseModel):
    cierre_id: int
    caja_id: int
    cajero_id: int
    total_esperado: Decimal
    total_registrado: Decimal
    diferencia: Decimal
    marcado_para_revision: bool
    fecha_hora: datetime


class CierreTiendaItem(BaseModel):
    caja_id: int
    cierre_id: int
    cajero_id: int
    total_esperado: Decimal
    total_registrado: Decimal
    diferencia: Decimal
    marcado_para_revision: bool
    fecha_hora: datetime


# ============================================================ datáfonos (US2)
class DatafonoOut(BaseModel):
    datafono_id: int
    caja_id: int
    modelo: str | None
    version_firmware: str | None
    fecha_ultima_actualizacion: date | None
    estado: str

    model_config = {"from_attributes": True}


class ActualizarDatafonoIn(BaseModel):
    version_firmware_nueva: str = Field(min_length=1, max_length=30)


class ConfiguracionSeguridadOut(BaseModel):
    config_id: int
    version_minima_firmware: str
    vigente_desde: date
    actualizado_por: int
    fecha_creacion: datetime

    model_config = {"from_attributes": True}


class DefinirEstandarSeguridadIn(BaseModel):
    version_minima_firmware: str = Field(min_length=1, max_length=30)


# ============================================================ reporte / escalamiento (US3)
class CuadreTurnoOut(BaseModel):
    cajero_id: int
    apertura_id: int
    fecha_turno: date | None
    suma_diferencias: Decimal
    cantidad_cuadres_con_diferencia: int


class AjusteSenaladoOut(BaseModel):
    ajuste_id: int
    product_id: int
    tienda_id: int
    diferencia: int
    empleado_id: int
    fecha: date


class ReporteDiferenciasOut(BaseModel):
    cuadres: list[CuadreTurnoOut]
    ajustes_senalados: list[AjusteSenaladoOut]


class IncidenteFraudeIn(BaseModel):
    empleado_id: int
    cierre_id: int | None = None
    ajuste_id: int | None = None
    descripcion: str = Field(min_length=1)


class IncidenteFraudeOut(BaseModel):
    incidente_id: int
    empleado_id: int
    cierre_id: int | None
    ajuste_id: int | None
    descripcion: str
    acciones_tomadas: str | None
    resultado: str | None
    estado: str
    actualizado_por: int | None
    fecha_actualizacion: datetime | None
    fecha_hora: datetime

    model_config = {"from_attributes": True}


# ============================================================ protocolo (US4)
class ProtocoloEscalamientoOut(BaseModel):
    protocolo_id: int
    texto: str
    definido_por: int
    fecha_creacion: datetime

    model_config = {"from_attributes": True}


class DefinirProtocoloIn(BaseModel):
    texto: str = Field(min_length=1)


class AplicarProtocoloIn(BaseModel):
    acciones_tomadas: str = Field(min_length=1)


class CerrarIncidenteIn(BaseModel):
    resultado: str = Field(pattern="^(fraude_confirmado|descartado)$")


# ============================================================ umbral de merma (US5)
class UmbralMermaOut(BaseModel):
    product_category: str
    porcentaje_umbral: Decimal
    definido_por: int
    fecha_actualizacion: datetime

    model_config = {"from_attributes": True}


class DefinirUmbralMermaIn(BaseModel):
    porcentaje_umbral: Decimal = Field(gt=0, le=100)


class SeguimientoMermaOut(BaseModel):
    product_category: str
    porcentaje_merma_acumulado: Decimal | None
    porcentaje_umbral: Decimal
    supera_umbral: bool
