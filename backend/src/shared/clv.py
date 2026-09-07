"""CLV compuesto (research.md §1, FR-005).

    clv_score (0..1) = 0.5 · frecuencia_norm + 0.5 · margen_norm

sobre una ventana móvil de 180 días. Cada componente se normaliza contra el
**percentil 95** (no el máximo) de esa señal entre los clientes activos de la
misma ventana, truncado a 1.0 — así un solo cliente atípico no comprime la
escala para todos. Nunca es sólo el gasto bruto acumulado (requisito duro).
"""

from __future__ import annotations

import math
from decimal import Decimal

VENTANA_DIAS = 180
PESO_FRECUENCIA = 0.5
PESO_MARGEN = 0.5


def percentil_95(valores: list[float]) -> float:
    """Percentil 95 por interpolación lineal (método 'linear' de numpy).
    Devuelve 0.0 si no hay datos."""
    datos = sorted(float(v) for v in valores)
    if not datos:
        return 0.0
    if len(datos) == 1:
        return datos[0]
    pos = 0.95 * (len(datos) - 1)
    bajo = math.floor(pos)
    alto = math.ceil(pos)
    if bajo == alto:
        return datos[int(pos)]
    return datos[bajo] + (datos[alto] - datos[bajo]) * (pos - bajo)


def _norm(valor: float, referencia: float) -> float:
    if referencia <= 0:
        return 0.0
    return min(1.0, valor / referencia)


def clv_score(
    frecuencia: float,
    margen: float,
    frecuencia_p95: float,
    margen_p95: float,
) -> Decimal:
    """Score de un cliente dados sus totales de la ventana y los percentiles 95
    de la población. Redondeado a 2 decimales (escala de `cliente_clv.clv_score`)."""
    score = PESO_FRECUENCIA * _norm(frecuencia, frecuencia_p95) + PESO_MARGEN * _norm(
        margen, margen_p95
    )
    return Decimal(str(round(score, 2)))
