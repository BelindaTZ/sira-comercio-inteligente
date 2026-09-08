"""T009 + T010 — cálculo del total esperado por cajero sobre la ventana horaria y
marcado automático para revisión (FR-003, FR-004, Principio X, research.md
Decisión 1/2). Incluye el caso de una ventana sin ninguna venta.
"""

from datetime import datetime
from decimal import Decimal

from src.shared.caja import marcado_para_revision, total_esperado_ventana

DESDE = datetime(2026, 9, 7, 9, 0, 0)
HASTA = datetime(2026, 9, 7, 10, 0, 0)


def _venta(minuto: int, total: str) -> dict:
    return {"fecha_hora": datetime(2026, 9, 7, 9, minuto, 0), "total": Decimal(total)}


def test_total_esperado_suma_las_ventas_de_la_ventana():
    ventas = [_venta(5, "10.00"), _venta(30, "5.50"), _venta(59, "4.00")]
    assert total_esperado_ventana(ventas, desde=DESDE, hasta=HASTA) == Decimal("19.50")


def test_ventana_sin_ninguna_venta_da_cero_no_none():
    assert total_esperado_ventana([], desde=DESDE, hasta=HASTA) == Decimal("0.00")


def test_excluye_ventas_fuera_de_la_ventana():
    ventas = [
        {"fecha_hora": datetime(2026, 9, 7, 8, 59), "total": Decimal("99.00")},  # antes
        {"fecha_hora": datetime(2026, 9, 7, 10, 1), "total": Decimal("99.00")},  # después
        _venta(15, "7.00"),
    ]
    assert total_esperado_ventana(ventas, desde=DESDE, hasta=HASTA) == Decimal("7.00")


def test_limite_inferior_excluyente_superior_incluyente():
    # una venta exactamente en `desde` NO cuenta (ya la contó el cuadre anterior);
    # una venta exactamente en `hasta` SÍ cuenta.
    ventas = [
        {"fecha_hora": DESDE, "total": Decimal("1.00")},
        {"fecha_hora": HASTA, "total": Decimal("2.00")},
    ]
    assert total_esperado_ventana(ventas, desde=DESDE, hasta=HASTA) == Decimal("2.00")


def test_marcado_para_revision_solo_si_hay_diferencia():
    assert marcado_para_revision(Decimal("-3.00")) is True
    assert marcado_para_revision(Decimal("0.01")) is True
    assert marcado_para_revision(Decimal("0.00")) is False
    assert marcado_para_revision(0) is False
