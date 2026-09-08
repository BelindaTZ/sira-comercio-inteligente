"""Esquemas Pydantic del módulo Direccion —
`specs/009-dashboards-multinivel/contracts/dashboards-multinivel.md` #1.

El mismo shape (`DashboardConsolidadoOut`) lo reutiliza el dashboard táctico de
`modules/ti/dashboards` (contracts #2, respuesta idéntica con `kpis` filtrados).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class DashboardKpiOut(BaseModel):
    dimension: str
    nombre_kpi: str
    valor: Decimal | None
    disponible: bool

    model_config = {"from_attributes": True}


class DashboardConsolidadoOut(BaseModel):
    publicacion_id: int
    fecha_publicacion: datetime
    kpis: list[DashboardKpiOut]
