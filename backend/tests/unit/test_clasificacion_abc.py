"""T028 + T029 — clasificación ABC por Pareto y exclusión por precio pendiente
(FR-009, FR-013, Principio X, research.md Decisiones 5 y 7).
"""

from src.modules.promociones.analytics.clasificacion_abc import (
    clasificar_categoria,
    excluir_con_precio_pendiente,
)


def test_pareto_clasifico_por_valor_acumulado():
    # 1 producto concentra el 80 % del valor → A; el resto reparte B/C.
    valores = {10: 800.0, 20: 120.0, 30: 50.0, 40: 30.0}
    clas = clasificar_categoria(valores, umbral_a=0.80, umbral_b=0.95)
    assert clas[10] == "A"
    assert clas[20] == "B"
    assert clas[30] == "C" and clas[40] == "C"


def test_producto_sin_ventas_cae_en_c():
    valores = {10: 500.0, 20: 0.0}
    assert clasificar_categoria(valores)[20] == "C"


def test_categoria_sin_ninguna_venta_todo_c():
    assert clasificar_categoria({1: 0.0, 2: 0.0}) == {1: "C", 2: "C"}


def test_orden_deterministico_por_product_id_en_empate():
    valores = {2: 100.0, 1: 100.0, 3: 100.0}
    clas = clasificar_categoria(valores, umbral_a=0.34, umbral_b=0.67)
    # acumulado: pid 1 (33%) → A ; pid 2 (67%) → B ; pid 3 (100%) → C
    assert clas == {1: "A", 2: "B", 3: "C"}


def test_excluye_productos_con_ajuste_de_precio_pendiente():
    assert excluir_con_precio_pendiente([1, 2, 3, 4], {2, 4}) == [1, 3]
    assert excluir_con_precio_pendiente([1, 2], set()) == [1, 2]
