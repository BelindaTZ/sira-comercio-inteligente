"""T009 — cálculo del margen real por línea (FR-002, Principio X).

Requisito duro: usa el precio YA descontado (no el de catálogo) y el costo
vigente, para TODA línea confirmada (no sólo las que tuvieron descuento manual).
"""

from decimal import Decimal

import pytest
from src.shared.pricing import margen_real_pct


def test_margen_sobre_precio_de_catalogo_sin_descuento():
    # precio 10.00, costo 6.00 → margen = 40%
    assert margen_real_pct(Decimal("10.00"), Decimal("6.00")) == Decimal("40.00")


def test_usa_el_precio_ya_descontado_no_el_de_catalogo():
    # catálogo 10.00, costo 6.00; con el precio descontado a 7.00 el margen baja.
    con_descuento = margen_real_pct(Decimal("7.00"), Decimal("6.00"))
    sin_descuento = margen_real_pct(Decimal("10.00"), Decimal("6.00"))
    assert con_descuento == Decimal("14.29")
    assert con_descuento < sin_descuento


def test_margen_puede_ser_negativo_si_se_vende_bajo_costo():
    assert margen_real_pct(Decimal("5.00"), Decimal("6.00")) == Decimal("-20.00")


@pytest.mark.parametrize("precio", [Decimal("0"), Decimal("-1")])
def test_precio_no_positivo_no_calcula(precio):
    assert margen_real_pct(precio, Decimal("6.00")) is None


def test_sin_costo_vigente_no_calcula():
    assert margen_real_pct(Decimal("10.00"), None) is None
