"""Reglas de asociación de canasta con `mlxtend` (research.md Decisión 1, Principio X).

`apriori` sobre una matriz binaria transacción×producto, `association_rules` para
derivar reglas antecedente→consecuente con soporte/confianza/lift. Sólo se
conservan reglas 1→1 (un antecedente, un consecuente) — son las accionables como
recomendación de cross-sell en el punto de venta.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules


def matriz_transacciones(lineas: Iterable[dict]) -> pd.DataFrame:
    """`lineas` = filas `{venta_id, product_id}` de `venta_detalle`. Devuelve una
    matriz booleana con una fila por `venta_id` y una columna por `product_id`."""
    df = pd.DataFrame(list(lineas))
    if df.empty:
        return df
    conteo = df.assign(_v=1).pivot_table(
        index="venta_id", columns="product_id", values="_v", aggfunc="max", fill_value=0
    )
    return conteo.gt(0)


def calcular_reglas(
    matriz: pd.DataFrame, soporte_minimo: float, confianza_minima: float
) -> list[dict]:
    """Reglas 1→1 que superan el soporte y la confianza mínimos. Lista vacía si no
    hay suficientes transacciones o ninguna regla supera los umbrales (Edge Case:
    no se fuerza una recomendación con evidencia insuficiente)."""
    if matriz.empty or len(matriz) < 2:
        return []

    frecuentes = apriori(matriz, min_support=max(soporte_minimo, 1e-9), use_colnames=True)
    if frecuentes.empty:
        return []

    reglas = association_rules(frecuentes, metric="confidence", min_threshold=confianza_minima)
    salida: list[dict] = []
    for _, fila in reglas.iterrows():
        antecedente = list(fila["antecedents"])
        consecuente = list(fila["consequents"])
        if len(antecedente) != 1 or len(consecuente) != 1:
            continue  # sólo reglas 1→1
        if float(fila["support"]) < soporte_minimo:
            continue
        salida.append(
            {
                "antecedente": int(antecedente[0]),
                "consecuente": int(consecuente[0]),
                "soporte": round(float(fila["support"]), 6),
                "confianza": round(float(fila["confidence"]), 6),
                "lift": round(float(fila["lift"]), 4),
            }
        )
    return salida


def mejor_recomendacion(reglas_vigentes: list[dict], carrito: set[int]) -> dict | None:
    """FR-003/FR-004/FR-005 — de las reglas vigentes cuyo antecedente está en el
    carrito y cuyo consecuente NO está, devuelve la de mayor confianza (desempate
    por soporte, luego por `consecuente` para determinismo). `None` si ninguna
    aplica."""
    aplicables = [
        r
        for r in reglas_vigentes
        if r["antecedente"] in carrito and r["consecuente"] not in carrito
    ]
    if not aplicables:
        return None
    return max(
        aplicables,
        key=lambda r: (float(r["confianza"]), float(r["soporte"]), -int(r["consecuente"])),
    )
