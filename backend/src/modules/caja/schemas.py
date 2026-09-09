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
    motivo_fuera_servicio: str | None = None

    model_config = {"from_attributes": True}


class FueraServicioIn(BaseModel):
    """FR-001 (007) + feature 013 — el Encargado deja constancia del motivo."""

    motivo: str = Field(min_length=1, max_length=200)


class ActualizarDatafonoIn(BaseModel):
    version_firmware_nueva: str = Field(min_length=1, max_length=30)


class DatafonoIn(BaseModel):
    """FR-006 — alta de un datáfono en el inventario. El estado de conformidad lo
    calcula el sistema contra el estándar vigente, no se recibe del cliente."""

    caja_id: int
    modelo: str | None = Field(default=None, max_length=60)
    version_firmware: str | None = Field(default=None, max_length=30)
    fecha_ultima_actualizacion: date | None = None


class DatafonoEditIn(BaseModel):
    """FR-006 — edición de los datos de inventario de un datáfono. Todos los
    campos son opcionales; el estado de conformidad se recalcula al guardar."""

    modelo: str | None = Field(default=None, max_length=60)
    version_firmware: str | None = Field(default=None, max_length=30)
    fecha_ultima_actualizacion: date | None = None


class CajaOut(BaseModel):
    caja_id: int
    tienda_id: int
    nombre: str
    activa: bool

    model_config = {"from_attributes": True}


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


# ============================================================ feature 007: pagos y seguridad
class DatafonoRestablecidoOut(BaseModel):
    datafono_id: int
    estado: str  # 'activo' | 'requiere_actualizacion' — nunca 'fuera_servicio'


class IncidenteSeguridadIn(BaseModel):
    datafono_id: int | None = None
    descripcion: str = Field(min_length=1)


class IncidenteSeguridadOut(BaseModel):
    incidente_seguridad_id: int
    datafono_id: int | None
    registrado_por: int
    descripcion: str
    estado: str
    actualizado_por: int | None
    fecha_actualizacion: datetime | None
    fecha_hora: datetime

    model_config = {"from_attributes": True}


class TransicionarIncidenteSeguridadIn(BaseModel):
    estado_nuevo: str = Field(pattern="^(en_investigacion|cerrado)$")


class ConteoIncidentesSeguridadOut(BaseModel):
    total: int
    periodo: dict[str, date | None]


class PoliticaSeguridadPagosOut(BaseModel):
    politica_id: int
    texto: str
    definido_por: int
    fecha_creacion: datetime

    model_config = {"from_attributes": True}


class DefinirPoliticaIn(BaseModel):
    texto: str = Field(min_length=1)
