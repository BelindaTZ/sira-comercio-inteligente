"""Clasificación ABC por valor de venta acumulado — Pareto clásico de inventarios
(research.md Decisión 5, Principio X).

Dentro de cada `product_category`, se ordenan los productos por su valor de venta
del periodo y se clasifican por contribución acumulada: A el primer ~80 % del
valor, B hasta ~95 %, C el resto. Un producto sin ventas cae siempre en C.
"""

from __future__ import annotations

UMBRAL_A_DEFAULT = 0.80
UMBRAL_B_DEFAULT = 0.95


def clasificar_categoria(
    valores: dict[int, float],
    *,
    umbral_a: float = UMBRAL_A_DEFAULT,
    umbral_b: float = UMBRAL_B_DEFAULT,
) -> dict[int, str]:
    """`valores` = `{product_id: valor_de_venta_del_periodo}` de UNA categoría.
    Devuelve `{product_id: 'A'|'B'|'C'}`."""
    total = sum(v for v in valores.values() if v > 0)
    if total <= 0:
        return {pid: "C" for pid in valores}

    # orden descendente por valor; desempate por product_id para determinismo
    ordenados = sorted(valores.items(), key=lambda kv: (-kv[1], kv[0]))
    salida: dict[int, str] = {}
    acumulado = 0.0
    for pid, valor in ordenados:
        if valor <= 0:
            salida[pid] = "C"
            continue
        acumulado += valor
        fraccion = acumulado / total
        if fraccion <= umbral_a:
            salida[pid] = "A"
        elif fraccion <= umbral_b:
            salida[pid] = "B"
        else:
            salida[pid] = "C"
    return salida


def excluir_con_precio_pendiente(
    candidatos: list[int], product_ids_con_precio_pendiente: set[int]
) -> list[int]:
    """FR-013 / research.md Decisión 7 — un producto con una propuesta de ajuste de
    precio pendiente en 003 no se ofrece como candidato a liquidación."""
    return [pid for pid in candidatos if pid not in product_ids_con_precio_pendiente]
