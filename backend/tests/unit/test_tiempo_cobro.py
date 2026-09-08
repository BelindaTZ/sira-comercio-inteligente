"""T039 — cálculo de duración de cobro (`fecha_hora - fecha_inicio_cobro`),
excluyendo ventas con `fecha_inicio_cobro IS NULL` y ventas anuladas
(FR-015, FR-018, Principio X).
"""

from datetime import datetime, timedelta

from src.shared.pagos import duracion_cobro_segundos, promedio_duracion_cobro

INICIO = datetime(2026, 9, 8, 10, 0, 0)


def _venta(inicio, delta_seg, estado="confirmada"):
    return {
        "fecha_inicio_cobro": inicio,
        "fecha_hora": inicio + timedelta(seconds=delta_seg) if inicio else None,
        "estado": estado,
    }


def test_duracion_simple():
    assert duracion_cobro_segundos(INICIO, INICIO + timedelta(seconds=45), "confirmada") == 45.0


def test_venta_sin_fecha_inicio_cobro_se_excluye():
    assert duracion_cobro_segundos(None, INICIO, "confirmada") is None


def test_venta_anulada_se_excluye():
    assert duracion_cobro_segundos(INICIO, INICIO + timedelta(seconds=30), "anulada") is None


def test_duracion_negativa_se_descarta():
    assert duracion_cobro_segundos(INICIO, INICIO - timedelta(seconds=5), "confirmada") is None


def test_promedio_excluye_anuladas_y_sin_inicio():
    ventas = [
        _venta(INICIO, 20),
        _venta(INICIO, 40),
        _venta(INICIO, 999, estado="anulada"),  # excluida
        _venta(None, 0),  # sin inicio → excluida
    ]
    promedio, consideradas = promedio_duracion_cobro(ventas)
    assert promedio == 30.0
    assert consideradas == 2


def test_promedio_sin_ventas_validas():
    assert promedio_duracion_cobro([_venta(None, 0), _venta(INICIO, 5, "anulada")]) == (None, 0)
