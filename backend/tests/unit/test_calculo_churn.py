"""T026 — ciclo de compra individual + severidad de riesgo de fuga (FR-009, FR-010).

La severidad siempre es relativa al ciclo **propio** de cada cliente (1.5x / 3x),
nunca un umbral fijo de días igual para todos (requisito duro, research §2).
"""

from datetime import date, timedelta
from decimal import Decimal

from src.shared.churn import ciclo_compra_dias, score_churn, severidad


def _fechas(*offsets_dias: int) -> list[date]:
    hoy = date(2026, 1, 1)
    return [hoy + timedelta(days=d) for d in offsets_dias]


def test_ciclo_none_con_menos_de_dos_compras():
    assert ciclo_compra_dias([]) is None
    assert ciclo_compra_dias(_fechas(0)) is None


def test_ciclo_es_promedio_de_intervalos_consecutivos():
    # compras cada 10 días exactos → ciclo 10
    assert ciclo_compra_dias(_fechas(0, 10, 20, 30)) == 10
    # intervalos 5 y 15 → promedio 10
    assert ciclo_compra_dias(_fechas(0, 5, 20)) == 10


def test_ciclo_toma_solo_las_ultimas_diez_compras():
    # 20 compras: las 10 primeras cada 100 días, las 10 últimas cada 2 días.
    viejas = list(range(0, 1000, 100))  # 10 fechas muy espaciadas
    recientes = list(range(1000, 1020, 2))  # 10 fechas juntas
    ciclo = ciclo_compra_dias(_fechas(*viejas, *recientes))
    # sólo cuentan las últimas 10 → 9 intervalos de 2 días
    assert ciclo == 2


def test_ciclo_ignora_fechas_duplicadas():
    assert ciclo_compra_dias(_fechas(0, 0, 10, 10, 20)) == 10


def test_severidad_en_riesgo_pasa_1_5x_pero_no_3x():
    # ciclo 10 → en_riesgo si dias > 15, inactivo si dias > 30
    assert severidad(16, 10) == "en_riesgo"
    assert severidad(30, 10) == "en_riesgo"
    assert severidad(15, 10) is None
    assert severidad(31, 10) == "inactivo"


def test_severidad_es_relativa_al_ciclo_no_a_un_umbral_fijo():
    # 40 días sin comprar: cliente de ciclo corto está inactivo; el de ciclo
    # largo sigue dentro de su patrón normal. Mismo `dias`, veredicto distinto.
    assert severidad(40, 10) == "inactivo"
    assert severidad(40, 60) is None


def test_severidad_none_si_ciclo_no_positivo():
    assert severidad(100, 0) is None


def test_score_churn_crece_hasta_uno_en_el_umbral_inactivo():
    assert score_churn(0, 10) == Decimal("0.0000")
    assert score_churn(15, 10) == Decimal("0.5000")  # 15 / 30
    assert score_churn(30, 10) == Decimal("1.0000")
    assert score_churn(90, 10) == Decimal("1.0000")  # truncado a 1
