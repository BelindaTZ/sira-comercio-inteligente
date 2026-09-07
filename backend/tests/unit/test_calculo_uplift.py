"""T040 — cálculo de uplift de campaña de reactivación (FR-018, Principio X).

El uplift compara la **tasa de retorno** del grupo tratado contra la del grupo
de control — nunca la tasa de redención del cupón.
"""

from decimal import Decimal

from src.shared.uplift import tasa_retorno, uplift


def test_tasa_retorno_es_proporcion_que_volvio():
    assert tasa_retorno(3, 10) == Decimal("0.3000")
    assert tasa_retorno(0, 10) == Decimal("0.0000")
    assert tasa_retorno(5, 5) == Decimal("1.0000")


def test_tasa_retorno_grupo_vacio_no_divide_por_cero():
    assert tasa_retorno(0, 0) == Decimal("0.0000")


def test_uplift_positivo_cuando_tratado_vuelve_mas():
    # 5/10 tratados vuelven, 2/10 de control → uplift +0.30
    assert uplift(tasa_retorno(5, 10), tasa_retorno(2, 10)) == Decimal("0.3000")


def test_uplift_cero_o_negativo_aunque_la_redencion_sea_alta():
    # Escenario clave: todos los tratados redimieron el cupón (redención 100%),
    # pero volvieron a comprar en la misma proporción que el control → uplift 0.
    # La redención no entra en el cálculo.
    tratado_volvieron, tratado_total = 4, 10
    control_volvieron, control_total = 4, 10
    resultado = uplift(
        tasa_retorno(tratado_volvieron, tratado_total),
        tasa_retorno(control_volvieron, control_total),
    )
    assert resultado == Decimal("0.0000")

    # y si el control vuelve más que el tratado, el uplift es negativo.
    assert uplift(tasa_retorno(2, 10), tasa_retorno(5, 10)) == Decimal("-0.3000")
