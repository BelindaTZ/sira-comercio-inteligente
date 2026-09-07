"""T019 — fórmula del precio propuesto por el motor de ajuste (FR-004, FR-005).

    precio_propuesto = precio_base * (1 - factor_sensibilidad * desviacion_pp / 100)

con piso duro en `costo * 1.01` (nunca proponer vender bajo costo).
"""

from decimal import Decimal

from src.shared.pricing import precio_propuesto


def test_margen_por_encima_del_objetivo_baja_el_precio():
    # desviacion_pp positiva (margen real > objetivo) → precio más bajo.
    nuevo = precio_propuesto(Decimal("10.00"), Decimal("0.3"), Decimal("4"), Decimal("6.00"))
    assert nuevo < Decimal("10.00")
    # 10 * (1 - 0.3*4/100) = 10 * 0.988 = 9.88
    assert nuevo == Decimal("9.88")


def test_margen_por_debajo_del_objetivo_sube_el_precio():
    nuevo = precio_propuesto(Decimal("10.00"), Decimal("0.3"), Decimal("-4"), Decimal("6.00"))
    assert nuevo == Decimal("10.12")


def test_nunca_propone_bajo_costo_mas_1pct():
    # desviacion enorme empujaría el precio bajo costo → se aplica el piso.
    nuevo = precio_propuesto(Decimal("10.00"), Decimal("0.5"), Decimal("90"), Decimal("6.00"))
    assert nuevo == Decimal("6.06")  # 6.00 * 1.01


def test_factor_cero_no_mueve_el_precio():
    assert precio_propuesto(
        Decimal("10.00"), Decimal("0"), Decimal("15"), Decimal("6.00")
    ) == Decimal("10.00")
