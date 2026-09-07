"""T032 — selección del producto ancla del cupón de hito (FR-013).

Sólo productos `es_ancla = true` y activos; entre ellos, el de mayor margen
vigente (`precio_base - costo`); desempate estable por `product_id`.
"""

from decimal import Decimal

from src.shared.cupon_hito import ProductoAncla, seleccionar_producto_ancla


def _p(pid, *, ancla=True, activo=True, precio="10.00", costo="4.00"):
    return ProductoAncla(pid, ancla, activo, Decimal(precio), Decimal(costo))


def test_sin_anclas_devuelve_none():
    assert seleccionar_producto_ancla([]) is None
    assert seleccionar_producto_ancla([_p(1, ancla=False)]) is None


def test_ignora_no_ancla_y_ancla_inactivo():
    productos = [
        _p(1, ancla=False, precio="100.00", costo="1.00"),  # margen enorme pero no es ancla
        _p(2, activo=False, precio="100.00", costo="1.00"),  # ancla pero inactivo
        _p(3, precio="10.00", costo="4.00"),  # único candidato válido
    ]
    assert seleccionar_producto_ancla(productos) == 3


def test_elige_el_de_mayor_margen_no_el_de_mayor_precio():
    productos = [
        _p(1, precio="20.00", costo="18.00"),  # margen 2
        _p(2, precio="12.00", costo="4.00"),  # margen 8  ← gana
        _p(3, precio="9.00", costo="6.00"),  # margen 3
    ]
    assert seleccionar_producto_ancla(productos) == 2


def test_desempate_estable_por_product_id_menor():
    productos = [_p(7, precio="10.00", costo="4.00"), _p(3, precio="10.00", costo="4.00")]
    assert seleccionar_producto_ancla(productos) == 3


def test_tolera_precio_o_costo_nulo():
    p = ProductoAncla(1, True, True, None, None)
    assert seleccionar_producto_ancla([p]) == 1
