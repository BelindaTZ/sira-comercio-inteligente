"""Ciclo de compra individual y severidad de riesgo de fuga (research.md §2,
FR-009/FR-010).

- `ciclo_compra_dias` = promedio de los intervalos (en días) entre compras
  consecutivas, sobre las **últimas 10 compras** del cliente (o todas si tiene
  menos de 10) — así un cambio de hábito reciente no queda diluido por historia
  vieja. Necesita >= 2 compras.
- Severidad, siempre relativa al ciclo **propio** del cliente (nunca un umbral
  fijo de días igual para todos):
    en_riesgo  : dias_desde_ultima > 1.5 × ciclo
    inactivo   : dias_desde_ultima > 3.0 × ciclo
    (ninguna)  : dentro de su patrón normal
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

MULT_EN_RIESGO = 1.5
MULT_INACTIVO = 3.0
VENTANA_COMPRAS = 10


def ciclo_compra_dias(fechas: list[date]) -> float | None:
    """Promedio de intervalos entre compras consecutivas (últimas 10)."""
    unicas = sorted(set(fechas))
    if len(unicas) < 2:
        return None
    recientes = unicas[-VENTANA_COMPRAS:]
    intervalos = [(recientes[i] - recientes[i - 1]).days for i in range(1, len(recientes))]
    return sum(intervalos) / len(intervalos)


def severidad(dias_desde_ultima: int, ciclo: float) -> str | None:
    if ciclo <= 0:
        return None
    if dias_desde_ultima > MULT_INACTIVO * ciclo:
        return "inactivo"
    if dias_desde_ultima > MULT_EN_RIESGO * ciclo:
        return "en_riesgo"
    return None


def score_churn(dias_desde_ultima: int, ciclo: float) -> Decimal:
    """Proxy 0..1: llega a 1.0 en el umbral de `inactivo` (3× el ciclo)."""
    if ciclo <= 0:
        return Decimal("0.0000")
    valor = min(1.0, dias_desde_ultima / (MULT_INACTIVO * ciclo))
    return Decimal(str(round(valor, 4)))
