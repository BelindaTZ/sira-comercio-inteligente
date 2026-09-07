"""T008 — cálculo de la métrica WAPE (research.md Decisión 5, Principio X).

WAPE = Σ|real − pronóstico| / Σ real. Requisito duro: una semana con demanda
real cero NO deja la métrica indefinida ni distorsiona el agregado.
"""

import pytest
from src.modules.forecasting.ml.metricas import wape


def test_wape_perfecto_es_cero():
    assert wape([10, 5, 8], [10, 5, 8]) == 0.0


def test_wape_agrega_antes_de_dividir():
    # errores 2 + 1 + 0 = 3 ; demanda real 10 + 5 + 8 = 23 → 3/23 ≈ 0.1304
    assert wape([10, 5, 8], [12, 4, 8]) == pytest.approx(0.1304, abs=1e-4)


def test_semana_con_demanda_cero_no_rompe_la_metrica():
    # el producto de la 2ª posición no vendió nada esa semana; el modelo predijo 1.
    resultado = wape([10, 0, 8], [10, 1, 8])
    assert resultado == pytest.approx(1 / 18, abs=1e-4)
    assert 0 <= resultado <= 1  # nunca inf ni NaN


def test_toda_la_demanda_real_cero_devuelve_valor_acotado():
    assert wape([0, 0], [0, 0]) == 0.0  # nada que medir
    assert wape([0, 0], [3, 1]) == 1.0  # error sin demanda: acotado a 1, no inf


def test_longitudes_distintas_es_error():
    with pytest.raises(ValueError):
        wape([1, 2], [1])
