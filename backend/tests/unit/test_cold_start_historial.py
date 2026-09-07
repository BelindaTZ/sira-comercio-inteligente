"""T009 — exclusión de productos/tienda sin historial suficiente (FR-006, Principio X).

Un (producto, tienda) con menos de `historial_minimo_semanas` de historial queda
FUERA del entrenamiento y cubierto por el respaldo de rotación reciente de 001.
"""

from src.modules.forecasting.ml.variables import (
    construir_dataset,
    pares_con_historial_suficiente,
)


def test_filtra_pares_bajo_el_minimo():
    conteo = {(1, 10): 20, (2, 10): 11, (3, 10): 12, (4, 10): 3}
    ok = pares_con_historial_suficiente(conteo, minimo_semanas=12)
    assert ok == {(1, 10), (3, 10)}
    assert (2, 10) not in ok  # 11 < 12
    assert (4, 10) not in ok  # cold start


def _serie(pid, tid, n):
    return [
        {
            "product_id": pid,
            "tienda_id": tid,
            "semana": s,
            "anio": 2025,
            "unidades": 5 + (s % 3),
            "promo": 0,
            "cambio_precio_pct": 0.0,
            "quiebre_propio": 0,
            "quiebre_categoria_pct": 0.0,
        }
        for s in range(1, n + 1)
    ]


def test_dataset_descarta_las_primeras_semanas_sin_rezagos():
    df = construir_dataset(_serie(1, 10, 10))
    # 10 semanas − 2 (lag_1, lag_2 no disponibles) = 8 filas utilizables
    assert len(df) == 8
    assert df["lag_1"].notna().all() and df["lag_2"].notna().all()


def test_dataset_vacio_devuelve_dataframe_vacio():
    assert construir_dataset([]).empty
