"""Selección del producto que ancla el cupón automático de hito (FR-013).

El cupón de cumpleaños/aniversario se emite sobre un producto **ancla**
(`es_ancla = true`, mismo concepto de 001 para productos que atraen tráfico —
no se inventa un tipo de "producto promocional", Principio VIII/DRY). Entre los
ancla activos se elige el de **mayor margen vigente** (`precio_base - costo`):
el cupón sale sobre el producto que más aguanta un descuento sin perder dinero.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProductoAncla:
    product_id: int
    es_ancla: bool
    activo: bool
    precio_base: Decimal | None
    costo: Decimal | None

    @property
    def margen(self) -> Decimal:
        return (self.precio_base or Decimal("0")) - (self.costo or Decimal("0"))


def seleccionar_producto_ancla(productos: list[ProductoAncla]) -> int | None:
    """`product_id` del ancla activo con mayor margen, o `None` si no hay ninguno.

    Desempate estable por `product_id` para que dos corridas del job den el mismo
    cupón mientras el catálogo no cambie.
    """
    candidatos = [p for p in productos if p.es_ancla and p.activo]
    if not candidatos:
        return None
    return max(candidatos, key=lambda p: (p.margen, -p.product_id)).product_id
