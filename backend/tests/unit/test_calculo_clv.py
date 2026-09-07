"""T019 — fórmula del CLV compuesto (FR-005, Principio X, research.md §1).

    clv_score = 0.5 · min(1, frecuencia/freq_p95) + 0.5 · min(1, margen/margen_p95)

Requisito duro: un cliente frecuente de margen bajo y otro de compra única de
margen alto NO se ordenan sólo por gasto/monto acumulado.
"""

from decimal import Decimal

from src.shared.clv import clv_score, percentil_95


def test_percentil_95_basico():
    assert percentil_95([]) == 0.0
    assert percentil_95([5]) == 5.0
    # 100 valores 1..100 → p95 ≈ 95.05
    assert 94 < percentil_95(list(range(1, 101))) < 97


def test_frecuente_margen_bajo_vs_unico_margen_alto_no_ordenan_por_monto():
    # A: 10 compras, margen 20 total.  B: 1 compra, margen 200 total.
    # Población: freq_p95 = 10, margen_p95 = 200.
    a = clv_score(frecuencia=10, margen=20, frecuencia_p95=10, margen_p95=200)
    b = clv_score(frecuencia=1, margen=200, frecuencia_p95=10, margen_p95=200)
    # A = 0.5·1 + 0.5·0.1 = 0.55 ;  B = 0.5·0.1 + 0.5·1 = 0.55
    assert a == b == Decimal("0.55")
    # Si el CLV fuera sólo el monto, B (200) aplastaría a A (20) — aquí empatan.


def test_pesa_frecuencia_y_margen_por_igual():
    solo_frecuencia = clv_score(10, 0, 10, 100)  # 0.5·1 + 0.5·0 = 0.5
    solo_margen = clv_score(0, 100, 10, 100)  # 0.5·0 + 0.5·1 = 0.5
    assert solo_frecuencia == solo_margen == Decimal("0.50")


def test_score_se_trunca_a_1_por_componente():
    # frecuencia y margen por encima del p95 → cada componente tope 1.0
    assert clv_score(50, 9999, 10, 100) == Decimal("1.00")


def test_sin_poblacion_el_score_es_cero():
    assert clv_score(5, 5, 0, 0) == Decimal("0.00")
