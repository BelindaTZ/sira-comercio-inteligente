"""Ingeniería de variables del pronóstico (research.md Decisión 3, FR-001/FR-006).

Una fila por producto×tienda×semana ya observada. Además del historial de ventas
(rezagos y promedio móvil), se agregan las variables exógenas que explican picos
que NO son demanda base sostenida: promoción activa, cambio de precio, quiebre de
stock propio y tasa de quiebre de la categoría.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

# Columnas de entrada del modelo (el objetivo es `unidades`).
FEATURES: list[str] = [
    "lag_1",
    "lag_2",
    "ma_4",
    "promo",
    "cambio_precio_pct",
    "quiebre_propio",
    "quiebre_categoria_pct",
    "semana",
]

_ORDEN = ["product_id", "tienda_id", "anio", "semana"]


def _semana_absoluta(df: pd.DataFrame) -> pd.Series:
    """Índice temporal global (año*53 + semana) para ordenar y particionar."""
    return df["anio"].astype(int) * 53 + df["semana"].astype(int)


def pares_con_historial_suficiente(
    conteo_semanas: dict[tuple[int, int], int], minimo_semanas: int
) -> set[tuple[int, int]]:
    """FR-006 / research.md Decisión 6 — los (producto, tienda) con al menos
    `minimo_semanas` de historial de ventas entran al entrenamiento; el resto
    queda cubierto por el respaldo de rotación reciente de 001."""
    return {par for par, n in conteo_semanas.items() if n >= minimo_semanas}


def construir_dataset(filas: Iterable[dict]) -> pd.DataFrame:
    """Convierte las filas semanales crudas en la matriz de entrenamiento con
    rezagos y promedio móvil calculados por (producto, tienda). Filas sin los dos
    rezagos disponibles (primeras semanas de cada serie) se descartan."""
    df = pd.DataFrame(list(filas))
    if df.empty:
        return df

    for col, default in (
        ("promo", 0),
        ("cambio_precio_pct", 0.0),
        ("quiebre_propio", 0),
        ("quiebre_categoria_pct", 0.0),
    ):
        if col not in df.columns:
            df[col] = default
        df[col] = df[col].fillna(default)

    df["_t"] = _semana_absoluta(df)
    df = df.sort_values(["product_id", "tienda_id", "_t"]).reset_index(drop=True)

    g = df.groupby(["product_id", "tienda_id"], sort=False)["unidades"]
    df["lag_1"] = g.shift(1)
    df["lag_2"] = g.shift(2)
    df["ma_4"] = g.shift(1).rolling(4, min_periods=1).mean().reset_index(drop=True)

    df = df.dropna(subset=["lag_1", "lag_2"]).reset_index(drop=True)
    return df


def fila_pronostico_base(
    ultimas_semanas: list[float], product_id: int, tienda_id: int, semana: int, anio: int
) -> dict:
    """Construye la fila de features para pronosticar UNA semana futura: las
    variables exógenas se ponen en su valor base (sin promoción, sin cambio de
    precio, sin quiebre) — el pronóstico es la demanda base esperada, no un pico
    circunstancial (spec.md Edge Case). `ultimas_semanas` = unidades de las
    semanas más recientes, la última primero."""
    recientes = [float(v) for v in ultimas_semanas][:4]
    lag_1 = recientes[0] if recientes else 0.0
    lag_2 = recientes[1] if len(recientes) > 1 else lag_1
    ma_4 = sum(recientes) / len(recientes) if recientes else 0.0
    return {
        "product_id": product_id,
        "tienda_id": tienda_id,
        "semana": semana,
        "anio": anio,
        "lag_1": lag_1,
        "lag_2": lag_2,
        "ma_4": ma_4,
        "promo": 0,
        "cambio_precio_pct": 0.0,
        "quiebre_propio": 0,
        "quiebre_categoria_pct": 0.0,
    }
