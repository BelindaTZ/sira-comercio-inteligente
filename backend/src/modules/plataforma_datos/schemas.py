"""Esquemas Pydantic del módulo Plataforma de Datos —
`specs/010-plataforma-datos-tactico-estrategico/contracts/plataforma-datos.md`.

Ronda 1 (post-implementación): base path real `/api/plataforma-datos` y formato
de error del proyecto `{"error": {...}}` — el contrato original decía
`/api/v1/ti/plataforma-datos` y `{"detail": ...}`; se alinea a las convenciones
reales del código (mismo criterio que la ronda 1 de 012).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ============================================================ US1: modelo de datos
class EntidadModeloCreate(BaseModel):
    nombre_entidad: str = Field(min_length=1, max_length=60)
    tipo: Literal["fact", "dimension"]
    tabla_origen_postgres: str = Field(min_length=1, max_length=60)
    descripcion: str | None = None


class EntidadModeloPatch(BaseModel):
    activa: bool | None = None
    descripcion: str | None = None

    @model_validator(mode="after")
    def _al_menos_un_campo(self) -> EntidadModeloPatch:
        if self.activa is None and self.descripcion is None:
            raise ValueError("indica al menos 'activa' o 'descripcion'")
        return self


class EntidadModeloOut(BaseModel):
    entidad_id: int
    nombre_entidad: str
    tipo: str
    tabla_origen_postgres: str
    descripcion: str | None
    activa: bool
    definido_por: int
    fecha_definicion: datetime

    model_config = {"from_attributes": True}


# ============================================================ US2/US3: corridas
class CorridaOut(BaseModel):
    corrida_id: int
    entidad_id: int
    nombre_entidad: str
    tipo_carga: str
    origen: str
    estado: str
    filas_cargadas: int | None
    filas_error: int
    fecha_inicio: datetime
    fecha_fin: datetime | None
    duracion_segundos: int | None


class CorridasOut(BaseModel):
    corridas: list[CorridaOut]


class RegistroCalidadOut(BaseModel):
    descripcion_problema: str
    identificador_registro: str | None
    fecha_hora: datetime

    model_config = {"from_attributes": True}


class CalidadCorridaOut(BaseModel):
    corrida_id: int
    registros: list[RegistroCalidadOut]


# ============================================================ US4: política
class PoliticaCreate(BaseModel):
    texto: str = Field(min_length=1)


class PoliticaOut(BaseModel):
    politica_id: int
    texto: str
    definido_por: int
    fecha_creacion: datetime

    model_config = {"from_attributes": True}


# ============================================================ FR-012: forzar corrida (dev)
class ForzarCorridaIn(BaseModel):
    entidad_id: int
    tipo_carga: Literal["completa", "incremental"] = "incremental"


class ForzarCorridaOut(BaseModel):
    corrida_id: int
    estado: str
