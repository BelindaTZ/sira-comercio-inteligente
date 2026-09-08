"""Encargado_Tienda — lectura del catálogo de productos

`Encargado_Tienda` ya tiene el módulo `Comercial` visible (migración 0010, para
cerrar el listado diario de margen bajo de su tienda), pero a nivel de tabla sólo
podía leer `revision_margen_bajo`. Al abrir "Catálogo de productos" el backend
respondía 403 y la navegación (feature 013) ocultaba la opción.

Decisión de negocio: el Encargado de Tienda puede **consultar** el catálogo
maestro (precios, EAN, clasificación ABC) en modo sólo lectura — no lo edita.
Se añade `can_select` sobre `Comercial.productos`; insert/update/delete siguen
reservados a `Jefe_Comercial` / `Jefe_Operaciones`.

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'productos', true, false, false, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Comercial'
       JOIN role_permisos_modulo rpm
         ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
       WHERE r.nombre = 'Encargado_Tienda'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO UPDATE
         SET can_select = true""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    """DELETE FROM role_permisos_tabla rpt
       USING roles r, modulos m
       WHERE rpt.role_id = r.role_id AND rpt.modulo_id = m.modulo_id
         AND r.nombre = 'Encargado_Tienda' AND m.nombre = 'Comercial'
         AND rpt.nombre_tabla = 'productos'""",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
