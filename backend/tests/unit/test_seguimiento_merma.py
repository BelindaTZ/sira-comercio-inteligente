"""T044 — cálculo del porcentaje de merma acumulada semanal por categoría/tienda
(FR-018, research.md Decisión 9, Principio X).
"""

from decimal import Decimal

from src.shared.caja import porcentaje_merma, supera_umbral


def test_porcentaje_merma_sobre_valor_de_venta():
    # merma 50, ventas 1000 → 5.00 %
    assert porcentaje_merma(Decimal("50"), Decimal("1000")) == Decimal("5.00")


def test_sin_ventas_no_hay_porcentaje():
    assert porcentaje_merma(Decimal("50"), Decimal("0")) is None


def test_sin_merma_es_cero_por_ciento():
    assert porcentaje_merma(Decimal("0"), Decimal("1000")) == Decimal("0.00")


def test_supera_umbral_es_estricto_y_tolera_none():
    assert supera_umbral(Decimal("5.01"), Decimal("5.00")) is True
    assert supera_umbral(Decimal("5.00"), Decimal("5.00")) is False
    assert supera_umbral(None, Decimal("5.00")) is False
