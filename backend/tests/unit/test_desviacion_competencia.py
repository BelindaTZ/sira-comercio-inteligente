"""T042 — desviación frente al precio de referencia de competencia (FR-015, FR-016).

Requisito duro: la desviación se calcula sobre el precio de competencia más
reciente sin importar su fuente; un producto sin ningún dato no genera alerta
(Edge Case de `spec.md`: ausencia de dato ≠ desviación).
"""

from decimal import Decimal

from src.shared.pricing import desviacion_competencia_pct


def test_desviacion_porcentual_basica():
    # propio 10.00 vs competencia 9.00 → 10% por debajo (en valor absoluto).
    assert desviacion_competencia_pct(Decimal("10.00"), Decimal("9.00")) == Decimal("10.00")


def test_es_simetrica_en_valor_absoluto():
    assert desviacion_competencia_pct(Decimal("10.00"), Decimal("11.00")) == Decimal("10.00")


def test_sin_precio_de_competencia_no_hay_desviacion():
    assert desviacion_competencia_pct(Decimal("10.00"), None) is None


def test_sin_precio_base_no_hay_desviacion():
    assert desviacion_competencia_pct(None, Decimal("9.00")) is None
    assert desviacion_competencia_pct(Decimal("0"), Decimal("9.00")) is None
