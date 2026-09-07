"""T009 + T010 — motor de afinidad de canasta (FR-001, FR-005, Principio X).

T009: filtrado de reglas por soporte/confianza mínimos configurados.
T010: selección de la regla de mayor confianza cuando varias aplican al carrito.
"""

import pandas as pd
from src.modules.promociones.analytics.afinidad import (
    calcular_reglas,
    matriz_transacciones,
    mejor_recomendacion,
)


def _tickets(pares):
    filas = []
    for venta_id, productos in enumerate(pares, start=1):
        for p in productos:
            filas.append({"venta_id": venta_id, "product_id": p})
    return filas


def test_par_frecuente_genera_regla_por_encima_del_umbral():
    # A y B juntos en 8 de 10 tickets → soporte 0.8, confianza alta
    tickets = _tickets([[1, 2]] * 8 + [[1]] + [[3]])
    reglas = calcular_reglas(
        matriz_transacciones(tickets), soporte_minimo=0.1, confianza_minima=0.5
    )
    pares = {(r["antecedente"], r["consecuente"]) for r in reglas}
    assert (1, 2) in pares or (2, 1) in pares


def test_par_raro_no_genera_regla_bajo_el_umbral_de_soporte():
    # A y B juntos en 1 de 20 tickets → soporte 0.05, por debajo de 0.10
    tickets = _tickets([[1, 2]] + [[1]] * 10 + [[2]] * 9)
    reglas = calcular_reglas(
        matriz_transacciones(tickets), soporte_minimo=0.10, confianza_minima=0.1
    )
    assert all((r["antecedente"], r["consecuente"]) != (1, 2) for r in reglas)


def test_confianza_baja_no_genera_regla():
    # A aparece en 10 tickets, con B solo en 3 → confianza A→B = 0.3
    tickets = _tickets([[1, 2]] * 3 + [[1]] * 7)
    reglas = calcular_reglas(
        matriz_transacciones(tickets), soporte_minimo=0.1, confianza_minima=0.6
    )
    assert all(r["antecedente"] != 1 or r["consecuente"] != 2 for r in reglas)


def test_matriz_vacia_devuelve_lista_vacia():
    assert calcular_reglas(pd.DataFrame(), 0.1, 0.1) == []


def test_recomienda_la_regla_de_mayor_confianza():
    reglas = [
        {"antecedente": 1, "consecuente": 2, "soporte": 0.2, "confianza": 0.4},
        {"antecedente": 1, "consecuente": 3, "soporte": 0.1, "confianza": 0.9},
    ]
    mejor = mejor_recomendacion(reglas, carrito={1})
    assert mejor["consecuente"] == 3


def test_no_recomienda_un_consecuente_ya_en_el_carrito():
    reglas = [{"antecedente": 1, "consecuente": 2, "soporte": 0.2, "confianza": 0.9}]
    assert mejor_recomendacion(reglas, carrito={1, 2}) is None


def test_sin_regla_aplicable_devuelve_none():
    reglas = [{"antecedente": 5, "consecuente": 6, "soporte": 0.2, "confianza": 0.9}]
    assert mejor_recomendacion(reglas, carrito={1, 2}) is None
