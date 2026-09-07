"""Feature 002 — Ronda 5: documento_identidad del cliente + generador de household_id

Top-up idempotente del bloque "EXTENSIÓN — Feature 002 (ronda 5)" de
`01_operativo_postgres.sql`. Un DB nuevo ya lo trae vía la migración 0001.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-06

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    # FR-001 (Ronda 5): cédula/RUC opcional, única sólo cuando se proporciona.
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS documento_identidad VARCHAR(13)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_clientes_documento_identidad "
    "ON clientes(documento_identidad) WHERE documento_identidad IS NOT NULL",
    # Generador de household_id para altas nuevas (el dataset llega hasta 2500).
    "CREATE SEQUENCE IF NOT EXISTS clientes_household_id_seq AS INTEGER START WITH 900000",
    "ALTER TABLE clientes ALTER COLUMN household_id SET DEFAULT "
    "nextval('clientes_household_id_seq')",
    # RBAC: el maestro de cliente se opera en caja (alta/edición por Cajero/Encargado,
    # baja sólo por Encargado_Tienda). El patrón base sólo sembró Jefe_Marketing.
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, true
       FROM roles r, modulos m
       WHERE m.nombre = 'Marketing_CRM' AND r.nombre IN ('Cajero','Encargado_Tienda')
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, true, true,
              (r.nombre = 'Encargado_Tienda')
       FROM roles r
       JOIN modulos m ON m.nombre = 'Marketing_CRM'
       CROSS JOIN (VALUES ('clientes'), ('clientes_demograficos')) AS t(tabla)
       WHERE r.nombre IN ('Cajero','Encargado_Tienda')
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    # La baja (anonimización) la puede hacer también el Jefe_Marketing.
    """UPDATE role_permisos_tabla SET can_delete = true
       WHERE role_id = (SELECT role_id FROM roles WHERE nombre = 'Jefe_Marketing')
         AND nombre_tabla IN ('clientes','clientes_demograficos')""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "ALTER TABLE clientes ALTER COLUMN household_id DROP DEFAULT",
    "DROP SEQUENCE IF EXISTS clientes_household_id_seq",
    "DROP INDEX IF EXISTS uq_clientes_documento_identidad",
    "ALTER TABLE clientes DROP COLUMN IF EXISTS documento_identidad",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
