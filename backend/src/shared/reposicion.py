"""Punto de reposición dinámico (FR-020, research.md #5).

    punto = demanda_diaria × lead_time + stock_seguridad
    stock_seguridad = seguridad_pct × (demanda_diaria × lead_time)

Es decir `punto = demanda_diaria × lead_time × (1 + seguridad_pct)`, redondeado
hacia arriba (nunca se pide menos de lo que cubre el consumo esperado).

`demanda_diaria` = unidades vendidas en la ventana / días de la ventana
(media móvil, por defecto 14 días).
"""

from __future__ import annotations

import math


def demanda_diaria(unidades_vendidas: int, ventana_dias: int) -> float:
    if ventana_dias <= 0:
        return 0.0
    return unidades_vendidas / ventana_dias


def punto_reposicion(
    demanda_diaria_unidades: float,
    lead_time_dias: float,
    seguridad_pct: float,
) -> int:
    consumo_lead_time = demanda_diaria_unidades * lead_time_dias
    return math.ceil(consumo_lead_time * (1 + seguridad_pct))


def punto_reposicion_desde_ventas(
    unidades_vendidas: int,
    ventana_dias: int,
    lead_time_dias: float,
    seguridad_pct: float,
) -> int:
    return punto_reposicion(
        demanda_diaria(unidades_vendidas, ventana_dias), lead_time_dias, seguridad_pct
    )
