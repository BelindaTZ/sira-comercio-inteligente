"""Esquemas Pydantic de `ti/dashboards` —
`specs/009-dashboards-multinivel/contracts/dashboards-multinivel.md` #2-#5.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# El dashboard táctico reutiliza el shape del estratégico (contracts #2).
from src.modules.direccion.schemas import DashboardConsolidadoOut, DashboardKpiOut

__all__ = [
    "DashboardConsolidadoOut",
    "DashboardKpiOut",
    "DashboardOperativoEstadoOut",
    "VerificacionOperativosOut",
    "ForzarPublicacionOut",
]


class DashboardOperativoEstadoOut(BaseModel):
    tienda_id: int
    nombre_dashboard: str
    fecha_ultima_actualizacion: datetime | None
    disponible: bool

    model_config = {"from_attributes": True}


class VerificacionOperativosOut(BaseModel):
    publicacion_id: int
    fecha_verificacion: datetime
    estado_por_tienda: list[DashboardOperativoEstadoOut]


class ForzarPublicacionOut(BaseModel):
    publicacion_id: int
    estado: Literal["en_proceso", "publicado"]
