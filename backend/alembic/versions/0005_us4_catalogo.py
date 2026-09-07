"""US4 — catálogo: nombre/marca de producto, generador de product_id, RBAC Comercial

Top-up idempotente de la ronda 10 de `01_operativo_postgres.sql` (un DB nuevo ya
la trae vía la migración 0001). Cada sentencia es no-op si ya se aplicó.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-06

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    "ALTER TABLE productos ADD COLUMN IF NOT EXISTS nombre VARCHAR(200)",
    "ALTER TABLE productos ADD COLUMN IF NOT EXISTS marca VARCHAR(120)",
    "CREATE SEQUENCE IF NOT EXISTS productos_product_id_seq AS INTEGER START WITH 90000000",
    "ALTER TABLE productos ALTER COLUMN product_id SET DEFAULT nextval('productos_product_id_seq')",
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, true
       FROM roles r, modulos m
       WHERE m.nombre = 'Comercial' AND r.nombre IN ('Jefe_Comercial','Jefe_Operaciones')
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Comercial'
       CROSS JOIN (VALUES ('productos'), ('historial_precios'), ('margenes_objetivo')) AS t(tabla)
       WHERE r.nombre IN ('Jefe_Comercial','Jefe_Operaciones')
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    """DELETE FROM role_permisos_tabla
       WHERE modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Comercial')
         AND role_id IN (SELECT role_id FROM roles
                         WHERE nombre IN ('Jefe_Comercial','Jefe_Operaciones'))""",
    """DELETE FROM role_permisos_modulo
       WHERE modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Comercial')
         AND role_id IN (SELECT role_id FROM roles
                         WHERE nombre IN ('Jefe_Comercial','Jefe_Operaciones'))""",
    "ALTER TABLE productos ALTER COLUMN product_id DROP DEFAULT",
    "DROP SEQUENCE IF EXISTS productos_product_id_seq",
    "ALTER TABLE productos DROP COLUMN IF EXISTS marca",
    "ALTER TABLE productos DROP COLUMN IF EXISTS nombre",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
