"""Lógica pura de pricing/márgenes (Principio X: cálculo de margen = lógica crítica).

Cuatro cálculos, sin I/O, testeados de forma aislada:
  - `margen_real_pct`            — margen real de una línea (FR-002)
  - `margen_objetivo_efectivo`   — modificador fijo ancla/nicho + piso global (FR-007, research §3)
  - `precio_propuesto`           — fórmula del motor de ajuste (FR-004/FR-005, research.md §2)
  - `desviacion_competencia_pct` — desviación frente al precio de competencia (FR-015)

y la lista fija de roles que pueden autorizar un descuento manual (FR-009, research.md §4).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")

# research.md §3 — modificador fijo del margen objetivo efectivo.
MODIFICADOR_ANCLA_PP = Decimal("-5")
MODIFICADOR_NICHO_PP = Decimal("3")

# research.md §4 — roles habilitados para autorizar un descuento manual en caja
# (Encargado_Tienda "o superior"). Jefe_Marketing/Jefe_TI/Jefe_RRHH quedan fuera
# a propósito: no tienen autoridad operativa sobre una tienda ni sobre pricing.
ROLES_AUTORIZAN_DESCUENTO: frozenset[str] = frozenset(
    {
        "Encargado_Tienda",
        "Jefe_Comercial",
        "Jefe_Operaciones",
        "Jefe_Finanzas",
        "Gerente_General",
    }
)


def _d(valor) -> Decimal:
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def margen_real_pct(precio_unitario_aplicado, costo) -> Decimal | None:
    """Margen real de una línea, en % del precio de venta ya descontado (FR-002):

        (precio_aplicado - costo) / precio_aplicado * 100

    `precio_unitario_aplicado` es el precio post-descuento, nunca el de catálogo.
    Devuelve `None` si no hay costo vigente o el precio es 0 (no se puede calcular).
    """
    if costo is None:
        return None
    precio = _d(precio_unitario_aplicado)
    if precio <= 0:
        return None
    margen = (precio - _d(costo)) / precio * 100
    return margen.quantize(_CENT, rounding=ROUND_HALF_UP)


def margen_objetivo_efectivo(
    margen_objetivo_categoria,
    *,
    es_ancla: bool,
    margen_minimo_global,
) -> tuple[Decimal, Decimal, bool]:
    """`(margen_objetivo_efectivo, modificador_pp, piso_global_aplicado)` — FR-007.

    Suma el modificador fijo (`-5pp` ancla / `+3pp` nicho) al margen objetivo de la
    categoría y aplica un piso en `margen_minimo_global`. Si la categoría no tiene
    margen objetivo (`None`), se parte del piso global.
    """
    piso = _d(margen_minimo_global)
    modificador = MODIFICADOR_ANCLA_PP if es_ancla else MODIFICADOR_NICHO_PP
    base = piso if margen_objetivo_categoria is None else _d(margen_objetivo_categoria)
    efectivo = base + modificador
    if efectivo < piso:
        return piso.quantize(_CENT), modificador, True
    return efectivo.quantize(_CENT), modificador, False


def precio_propuesto(precio_base, factor_sensibilidad, desviacion_pp, costo) -> Decimal:
    """Precio propuesto por el motor de ajuste (research.md §2):

        precio_base * (1 - factor_sensibilidad * desviacion_pp / 100)

    con piso duro en `costo * 1.01` (nunca proponer vender bajo costo). `desviacion_pp`
    > 0 (margen real por encima del objetivo) → precio más bajo; < 0 → precio más alto.
    """
    bruto = _d(precio_base) * (Decimal("1") - _d(factor_sensibilidad) * _d(desviacion_pp) / 100)
    piso = _d(costo) * Decimal("1.01") if costo is not None else Decimal("0")
    return max(bruto, piso).quantize(_CENT, rounding=ROUND_HALF_UP)


def desviacion_competencia_pct(precio_base, precio_competencia) -> Decimal | None:
    """|precio_base - precio_competencia| / precio_base * 100 (FR-015). `None` si
    falta alguno de los dos o `precio_base` es 0 (ausencia de dato ≠ desviación)."""
    if precio_base is None or precio_competencia is None:
        return None
    base = _d(precio_base)
    if base <= 0:
        return None
    desv = abs(base - _d(precio_competencia)) / base * 100
    return desv.quantize(_CENT, rounding=ROUND_HALF_UP)


def rol_autoriza_descuento(rol: str | None) -> bool:
    """FR-009 / research.md §4 — ¿el rol puede autorizar un descuento manual?"""
    return rol in ROLES_AUTORIZAN_DESCUENTO
