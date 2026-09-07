"""Feature 002 — Ronda 7: RBAC de redención de cupón en caja (FR-015)

`POST /api/clientes/cupones/{upc}/redimir` lo ejecuta el Cajero al aplicar el
cupón en el punto de venta. El patrón base sólo sembró `cupon_redimido` para
Jefe_Marketing; falta el `INSERT` para el Cajero (ya tiene acceso al módulo
Marketing_CRM desde la ronda 5). Idempotente.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-07

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'cupon_redimido', true, true, false, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Marketing_CRM'
       JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
       WHERE r.nombre = 'Cajero'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    """DELETE FROM role_permisos_tabla
       WHERE nombre_tabla = 'cupon_redimido'
         AND modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Marketing_CRM')
         AND role_id = (SELECT role_id FROM roles WHERE nombre = 'Cajero')""",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
