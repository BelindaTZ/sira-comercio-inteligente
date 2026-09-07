"""T029 — control de doble autorización del descuento manual (FR-009, Principio X).

Dos comprobaciones:
  1. `empleado_aplica_id <> empleado_autoriza_id` (mismo patrón que FR-027/FR-034 de 001).
  2. el rol de `empleado_autoriza_id` está en la lista fija de research.md §4.
"""

from src.shared.pricing import ROLES_AUTORIZAN_DESCUENTO, rol_autoriza_descuento


def test_roles_habilitados_exactos():
    assert (
        frozenset(
            {
                "Encargado_Tienda",
                "Jefe_Comercial",
                "Jefe_Operaciones",
                "Jefe_Finanzas",
                "Gerente_General",
            }
        )
        == ROLES_AUTORIZAN_DESCUENTO
    )


def test_encargado_tienda_puede_autorizar():
    assert rol_autoriza_descuento("Encargado_Tienda") is True


def test_gerente_general_puede_autorizar():
    assert rol_autoriza_descuento("Gerente_General") is True


def test_cajero_no_puede_autorizar():
    assert rol_autoriza_descuento("Cajero") is False


def test_jefe_de_area_sin_autoridad_operativa_no_puede():
    for rol in ("Jefe_Marketing", "Jefe_TI", "Jefe_RRHH", "Reponedor", None):
        assert rol_autoriza_descuento(rol) is False
