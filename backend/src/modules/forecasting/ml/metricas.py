"""Métrica de precisión del pronóstico — WAPE (research.md Decisión 5, Principio X).

    WAPE = Σ |demanda_real − pronóstico| / Σ demanda_real

Se agrega el error y la demanda real por separado ANTES de dividir: así una
semana con demanda real cero en un producto no deja la métrica indefinida ni la
distorsiona (a diferencia del MAPE clásico). El resultado es un porcentaje
interpretable (0 = perfecto; 1 = el error total iguala a la demanda total).
"""

from __future__ import annotations

from collections.abc import Sequence


def wape(reales: Sequence[float], pronosticos: Sequence[float]) -> float:
    """WAPE sobre pares (real, pronóstico). Devuelve 0.0 si no hubo demanda ni
    error (nada que medir); 1.0 si hubo error pero la demanda real total fue cero
    (caso degenerado acotado, nunca `inf` ni `NaN`)."""
    if len(reales) != len(pronosticos):
        raise ValueError("reales y pronosticos deben tener la misma longitud")
    total_real = sum(abs(float(r)) for r in reales)
    total_error = sum(abs(float(r) - float(p)) for r, p in zip(reales, pronosticos, strict=True))
    if total_real == 0:
        return 0.0 if total_error == 0 else 1.0
    return round(total_error / total_real, 4)
