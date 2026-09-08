"""T020 — `GET medios-pago/disponibles` excluye medios no aprobados o dados de
baja (FR-007, Principio X).
"""

from datetime import datetime

from src.shared.pagos import medio_pago_disponible


def test_aprobado_y_sin_baja_esta_disponible():
    assert medio_pago_disponible(aprobado=True, fecha_baja=None) is True


def test_no_aprobado_no_esta_disponible():
    assert medio_pago_disponible(aprobado=False, fecha_baja=None) is False


def test_dado_de_baja_no_esta_disponible():
    assert medio_pago_disponible(aprobado=True, fecha_baja=datetime(2026, 1, 1)) is False
    # aunque siguiera marcado aprobado, la baja manda
    assert medio_pago_disponible(aprobado=False, fecha_baja=datetime(2026, 1, 1)) is False
