"""T044 — punto de reposición dinámico (FR-020, research.md #5).

punto = demanda_diaria × lead_time × (1 + seguridad_pct), redondeado hacia arriba
"""

from src.shared.reposicion import (
    demanda_diaria,
    punto_reposicion,
    punto_reposicion_desde_ventas,
)


def test_demanda_diaria_es_media_movil():
    assert demanda_diaria(140, 14) == 10.0
    assert demanda_diaria(0, 14) == 0.0
    assert demanda_diaria(5, 0) == 0.0  # sin división por cero


def test_punto_incluye_lead_time_y_seguridad():
    # 10 u/día × 7 días = 70; + 20% seguridad = 84
    assert punto_reposicion(10.0, 7, 0.20) == 84


def test_punto_redondea_hacia_arriba():
    # 3 u/día × 5 días = 15; ×1.2 = 18.0 exacto
    assert punto_reposicion(3.0, 5, 0.20) == 18
    # 1 u/día × 4 días = 4; ×1.2 = 4.8 → 5
    assert punto_reposicion(1.0, 4, 0.20) == 5


def test_sin_demanda_el_punto_es_cero():
    assert punto_reposicion(0.0, 7, 0.20) == 0


def test_desde_ventas_compone_ambos_pasos():
    # 280 vendidas / 14 días = 20 u/día; ×7 días ×1.2 = 168
    assert punto_reposicion_desde_ventas(280, 14, 7, 0.20) == 168
