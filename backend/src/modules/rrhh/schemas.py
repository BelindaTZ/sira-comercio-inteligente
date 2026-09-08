"""Esquemas Pydantic del módulo RRHH — `contracts/auth-administracion-sistema.md`."""

from __future__ import annotations

from datetime import date

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
