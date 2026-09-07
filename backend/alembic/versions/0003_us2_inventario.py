"""US2 — inventario por lotes: estado de validación de merma + RBAC de Operaciones

Top-up idempotente de la ronda 8 de `01_operativo_postgres.sql` (un DB nuevo ya
la trae vía la migración 0001). Cada sentencia es no-op si ya se aplicó.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-06

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    # spec.md Key Entities → Merma: lote + estado de validación
    "ALTER TABLE mermas ADD COLUMN IF NOT EXISTS lote_id BIGINT REFERENCES lotes(lote_id)",
    "ALTER TABLE mermas ADD COLUMN IF NOT EXISTS estado_validacion VARCHAR(20) NOT NULL DEFAULT 'pendiente'",
    "ALTER TABLE mermas ADD COLUMN IF NOT EXISTS empleado_valida_id INTEGER REFERENCES empleados(empleado_id)",
    "ALTER TABLE mermas ADD COLUMN IF NOT EXISTS fecha_validacion TIMESTAMP",
    (
        "DO $$ BEGIN "
        "ALTER TABLE mermas ADD CONSTRAINT chk_mermas_estado_validacion "
        "CHECK (estado_validacion IN ('pendiente','validada','rechazada')); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ),
    "CREATE INDEX IF NOT EXISTS idx_mermas_estado_validacion ON mermas(estado_validacion) "
    "WHERE estado_validacion = 'pendiente'",
    # RBAC del módulo Operaciones (no estaba sembrado)
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, true
       FROM roles r, modulos m
       WHERE m.nombre = 'Operaciones'
         AND r.nombre IN ('Reponedor','Encargado_Tienda','Jefe_Operaciones')
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla,
              true, true,
              (r.nombre <> 'Reponedor' OR t.tabla IN ('lotes','inventario')),
              false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Operaciones'
       CROSS JOIN (VALUES ('lotes'), ('recepcion_mercaderia'), ('ajustes_inventario'),
                           ('mermas'), ('inventario'), ('movimientos_inventario'),
                           ('ordenes_compra'), ('orden_compra_detalle')) AS t(tabla)
       WHERE r.nombre IN ('Reponedor','Encargado_Tienda','Jefe_Operaciones')
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    """DELETE FROM role_permisos_tabla
       WHERE modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Operaciones')
         AND role_id IN (SELECT role_id FROM roles
                         WHERE nombre IN ('Reponedor','Encargado_Tienda','Jefe_Operaciones'))""",
    """DELETE FROM role_permisos_modulo
       WHERE modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Operaciones')
         AND role_id IN (SELECT role_id FROM roles
                         WHERE nombre IN ('Reponedor','Encargado_Tienda','Jefe_Operaciones'))""",
    "DROP INDEX IF EXISTS idx_mermas_estado_validacion",
    "ALTER TABLE mermas DROP CONSTRAINT IF EXISTS chk_mermas_estado_validacion",
    "ALTER TABLE mermas DROP COLUMN IF EXISTS fecha_validacion",
    "ALTER TABLE mermas DROP COLUMN IF EXISTS empleado_valida_id",
    "ALTER TABLE mermas DROP COLUMN IF EXISTS estado_validacion",
    "ALTER TABLE mermas DROP COLUMN IF EXISTS lote_id",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
