"""T018 — margen objetivo efectivo por clasificación ancla/nicho (FR-007, Principio X).

Requisito duro (SC-003): un producto ancla y uno nicho de la MISMA categoría
nunca reciben el mismo margen objetivo efectivo; el piso global de respaldo nunca
se cruza.
"""

from decimal import Decimal

from src.shared.pricing import margen_objetivo_efectivo


def test_ancla_siempre_por_debajo_del_nicho_de_la_misma_categoria():
    ancla, mod_a, _ = margen_objetivo_efectivo(
        Decimal("20"), es_ancla=True, margen_minimo_global=Decimal("5")
    )
    nicho, mod_n, _ = margen_objetivo_efectivo(
        Decimal("20"), es_ancla=False, margen_minimo_global=Decimal("5")
    )
    assert ancla == Decimal("15.00")  # 20 - 5
    assert nicho == Decimal("23.00")  # 20 + 3
    assert ancla < nicho
    assert mod_a == Decimal("-5") and mod_n == Decimal("3")


def test_nunca_iguales_aunque_la_categoria_sea_baja():
    ancla, _, _ = margen_objetivo_efectivo(
        Decimal("8"), es_ancla=True, margen_minimo_global=Decimal("5")
    )
    nicho, _, _ = margen_objetivo_efectivo(
        Decimal("8"), es_ancla=False, margen_minimo_global=Decimal("5")
    )
    assert ancla != nicho


def test_piso_global_nunca_se_cruza():
    # 8 - 5 = 3 < piso 5 → se aplica el piso, y se reporta.
    efectivo, _, piso_aplicado = margen_objetivo_efectivo(
        Decimal("8"), es_ancla=True, margen_minimo_global=Decimal("5")
    )
    assert efectivo == Decimal("5.00")
    assert piso_aplicado is True


def test_categoria_sin_margen_objetivo_parte_del_piso():
    efectivo, _, _ = margen_objetivo_efectivo(
        None, es_ancla=False, margen_minimo_global=Decimal("5")
    )
    assert efectivo == Decimal("8.00")  # 5 + 3
