"""T028 + T029 — agrupación del reporte mensual por cajero + turno (no por el total
de la tienda) y señalización de ajustes de inventario anómalos (FR-009, FR-010,
research.md Decisión 3, Principio X).
"""

from datetime import date
from decimal import Decimal

from src.shared.caja import agrupar_diferencias_por_turno, ajuste_inventario_anomalo


def _cierre(cajero_id: int, apertura_id: int, diferencia: str) -> dict:
    return {
        "cajero_id": cajero_id,
        "apertura_id": apertura_id,
        "fecha_turno": date(2026, 9, 7),
        "diferencia": Decimal(diferencia),
    }


def test_agrupa_por_cajero_y_turno_no_por_tienda():
    cierres = [
        _cierre(1, 10, "-2.00"),
        _cierre(1, 10, "-3.00"),
        _cierre(1, 11, "1.00"),
        _cierre(2, 12, "0.00"),
    ]
    grupos = agrupar_diferencias_por_turno(cierres)
    assert len(grupos) == 3  # (1,10), (1,11), (2,12) — no un solo total de tienda

    turno_1_10 = next(g for g in grupos if (g["cajero_id"], g["apertura_id"]) == (1, 10))
    assert turno_1_10["suma_diferencias"] == Decimal("-5.00")
    assert turno_1_10["cantidad_cuadres_con_diferencia"] == 2


def test_cuadre_sin_diferencia_no_suma_al_contador():
    grupos = agrupar_diferencias_por_turno([_cierre(2, 12, "0.00")])
    assert grupos[0]["cantidad_cuadres_con_diferencia"] == 0
    assert grupos[0]["suma_diferencias"] == Decimal("0.00")


def test_ajuste_negativo_sobre_umbral_se_senala():
    assert ajuste_inventario_anomalo(-15, 10) is True
    assert ajuste_inventario_anomalo(-10, 10) is True  # alcanza el umbral


def test_ajuste_pequeno_o_positivo_no_se_senala():
    assert ajuste_inventario_anomalo(-3, 10) is False
    assert ajuste_inventario_anomalo(25, 10) is False  # sobra stock, no es faltante
    assert ajuste_inventario_anomalo(0, 10) is False
