"""Uplift de una campaña de reactivación (FR-018, requisito duro).

El uplift **nunca** se mide por la tasa de redención del cupón: se mide
comparando qué proporción del grupo **tratado** volvió a comprar tras el envío
contra la misma proporción del grupo de **control** (que no recibió incentivo).
La resta la hace la BD (columna generada `campana_resultado.uplift`); aquí sólo
se calculan las dos tasas de retorno.
"""

from __future__ import annotations

from decimal import Decimal


def tasa_retorno(volvieron: int, total: int) -> Decimal:
    """Proporción del grupo que registró al menos una compra tras el envío.
    `0.0000` si el grupo está vacío (no se puede dividir por cero)."""
    if total <= 0:
        return Decimal("0.0000")
    return Decimal(str(round(volvieron / total, 4)))


def uplift(tasa_tratado: Decimal, tasa_control: Decimal) -> Decimal:
    """Diferencia de tasas de retorno. La BD la recalcula como columna generada;
    esta función existe para el chequeo de la capa de servicio y los tests."""
    return (tasa_tratado - tasa_control).quantize(Decimal("0.0001"))
