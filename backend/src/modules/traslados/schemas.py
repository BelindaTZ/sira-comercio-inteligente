"""Esquemas Pydantic del módulo Traslados —
`specs/012-traslados-stock-entre-tiendas/contracts/traslados-stock-entre-tiendas.md`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class DisponibilidadTiendaItem(BaseModel):
    tienda_id: int
    nombre_tienda: str
    cantidad_disponible: int


class DisponibilidadSucursalesOut(BaseModel):
    product_id: int
    disponibilidad: list[DisponibilidadTiendaItem]


class TrasladoCreate(BaseModel):
    product_id: int
    tienda_origen_id: int
    tienda_destino_id: int
    cantidad: int = Field(gt=0)

    @model_validator(mode="after")
    def _origen_distinto_destino(self) -> TrasladoCreate:
        if self.tienda_origen_id == self.tienda_destino_id:
            raise ValueError("tienda_origen_id y tienda_destino_id deben ser distintas")
        return self


class TrasladoResolucion(BaseModel):
    decision: Literal["aprobar", "rechazar"]
    motivo: str | None = None


class TrasladoOut(BaseModel):
    traslado_id: int
    product_id: int
    tienda_origen_id: int
    tienda_destino_id: int
    cantidad: int
    estado: str
    empleado_id: int
    fecha_hora: datetime
    resuelto_por: int | None
    fecha_resolucion: datetime | None
    recibido_por: int | None
    fecha_recepcion: datetime | None
    fecha_cancelacion: datetime | None

    model_config = {"from_attributes": True}


class TrasladoReporteItem(TrasladoOut):
    pendiente_confirmacion: bool


class StockInsuficienteOut(BaseModel):
    detail: str
    stock_disponible: int
    cantidad_solicitada: int


class ReporteSemanalParams(BaseModel):
    desde: date
    hasta: date
