"""Entrenamiento del modelo global de pronóstico (research.md Decisiones 2 y 4).

Un único modelo de regresión (`scikit-learn`) sobre todas las combinaciones
producto×tienda×semana. La partición de validación es SIEMPRE temporal (las
últimas N semanas), nunca aleatoria — una partición aleatoria filtraría
información del futuro e inflaría la precisión medida.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from src.modules.forecasting.ml.metricas import wape
from src.modules.forecasting.ml.variables import FEATURES, _semana_absoluta

SEMANAS_VALIDACION_DEFAULT = 4


@dataclass(slots=True)
class ResultadoEntrenamiento:
    modelo: HistGradientBoostingRegressor
    wape_validacion: float
    filas_entrenamiento: int
    filas_validacion: int


def entrenar(
    dataset: pd.DataFrame, semanas_validacion: int = SEMANAS_VALIDACION_DEFAULT
) -> ResultadoEntrenamiento:
    """Entrena sobre `dataset` (salida de `variables.construir_dataset`) y mide el
    WAPE contra las últimas `semanas_validacion` semanas, que quedan fuera del
    entrenamiento."""
    if dataset.empty:
        raise ValueError("El dataset de entrenamiento está vacío")

    t = _semana_absoluta(dataset)
    semanas_ordenadas = sorted(t.unique())
    corte = (
        semanas_ordenadas[-semanas_validacion]
        if len(semanas_ordenadas) > semanas_validacion
        else semanas_ordenadas[-1]
    )
    train = dataset[t < corte]
    valid = dataset[t >= corte]
    if train.empty:  # serie demasiado corta: entrena con todo, valida con la última semana
        train = dataset[t < semanas_ordenadas[-1]]
        valid = dataset[t >= semanas_ordenadas[-1]]
    if train.empty:
        train = valid = dataset

    modelo = HistGradientBoostingRegressor(
        max_iter=200, learning_rate=0.08, max_depth=4, random_state=42
    )
    modelo.fit(train[FEATURES], train["unidades"].astype(float))

    pred = np.clip(modelo.predict(valid[FEATURES]), 0, None)
    wape_val = wape(valid["unidades"].tolist(), pred.tolist())

    return ResultadoEntrenamiento(
        modelo=modelo,
        wape_validacion=wape_val,
        filas_entrenamiento=len(train),
        filas_validacion=len(valid),
    )


def pronosticar(modelo: HistGradientBoostingRegressor, filas: pd.DataFrame) -> np.ndarray:
    """Predice unidades demandadas (nunca negativas) para las filas de features dadas."""
    if filas.empty:
        return np.array([])
    return np.clip(modelo.predict(filas[FEATURES]), 0, None)
