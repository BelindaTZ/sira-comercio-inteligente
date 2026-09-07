"""T020 — cálculo del total de venta línea a línea (sin redondeos incorrectos)."""

from decimal import Decimal

from src.modules.ventas.service import calcular_total


class _Linea:
    def __init__(self, sales_value, cantidad):
        self.sales_value = sales_value
        self.cantidad = cantidad


def test_total_vacio_es_cero():
    assert calcular_total([]) == Decimal("0")


def test_total_suma_linea_a_linea():
    lineas = [_Linea(Decimal("2.50"), 3), _Linea(Decimal("1.99"), 2), _Linea(Decimal("10.00"), 1)]
    assert calcular_total(lineas) == Decimal("21.48")


def test_total_no_redondea_a_mitad_de_camino():
    # 0.10 * 3 = 0.30 exacto; un float acumularía 0.30000000000000004
    lineas = [_Linea(Decimal("0.10"), 1) for _ in range(3)]
    assert calcular_total(lineas) == Decimal("0.30")


def test_total_acepta_sales_value_como_str_o_float():
    lineas = [_Linea("2.50", 2), _Linea(1.25, 4)]
    assert calcular_total(lineas) == Decimal("10.00")
