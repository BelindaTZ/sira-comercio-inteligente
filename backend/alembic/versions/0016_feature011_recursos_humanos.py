"""Feature 011 — recursos humanos

Top-up idempotente del bloque "EXTENSIÓN — Feature 011" de
`01_operativo_postgres.sql` (data-model.md). Aplica sobre un DB en 0015.

- Extiende aditivamente `roles_puesto` con `es_critico` (FR-001).
- Crea `acciones_retencion` — única tabla nueva de la feature (research.md Decisión 1).
- RBAC: sin rol ni módulo nuevo. Extiende el módulo `RRHH` (primer uso por 008):
  `Jefe_RRHH` gana acceso a las tablas de esta feature; `Encargado_Tienda` recibe
  un nuevo acceso concedido de solo lectura a `empleado_capacitacion` (FR-005,
  patrón `Jefe_Marketing`→`Ventas` de 005 / `Jefe_Comercial`→`Ventas` de 007).

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    # ---- roles_puesto: marca de puesto crítico (FR-001) ----
    "ALTER TABLE roles_puesto ADD COLUMN IF NOT EXISTS es_critico BOOLEAN NOT NULL DEFAULT false",
    # ---- acciones_retencion (FR-002, research.md Decisión 1) ----
    """CREATE TABLE IF NOT EXISTS acciones_retencion (
        accion_id BIGSERIAL PRIMARY KEY,
        empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id) ON DELETE CASCADE,
        fecha DATE NOT NULL DEFAULT CURRENT_DATE,
        descripcion TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_acciones_retencion_empleado_id "
    "ON acciones_retencion(empleado_id)",
    # ---- RBAC — extiende el módulo `RRHH` (data-model.md, Extensión RBAC) ----
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, t.ins, t.upd, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'RRHH'
       JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
       CROSS JOIN (VALUES
            ('roles_puesto', false, true),
            ('acciones_retencion', true, false),
            ('capacitaciones', true, false),
            ('empleado_capacitacion', true, true),
            ('clima_laboral', true, false),
            ('plan_sucesion', true, false)
       ) AS t(tabla, ins, upd)
       WHERE r.nombre = 'Jefe_RRHH'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    # Encargado_Tienda: nuevo acceso concedido de solo lectura al módulo `RRHH` (FR-005).
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, false
       FROM roles r, modulos m
       WHERE m.nombre = 'RRHH' AND r.nombre = 'Encargado_Tienda'
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'empleado_capacitacion', true, false, false, false
       FROM roles r JOIN modulos m ON m.nombre = 'RRHH'
       WHERE r.nombre = 'Encargado_Tienda'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DELETE FROM role_permisos_tabla rpt USING roles r, modulos m "
    "WHERE rpt.role_id = r.role_id AND rpt.modulo_id = m.modulo_id AND m.nombre = 'RRHH' "
    "AND ((r.nombre = 'Jefe_RRHH' AND rpt.nombre_tabla IN "
    "     ('roles_puesto','acciones_retencion','capacitaciones','empleado_capacitacion',"
    "      'clima_laboral','plan_sucesion')) "
    "     OR (r.nombre = 'Encargado_Tienda' AND rpt.nombre_tabla = 'empleado_capacitacion'))",
    "DELETE FROM role_permisos_modulo rpm USING roles r, modulos m "
    "WHERE rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id "
    "AND m.nombre = 'RRHH' AND r.nombre = 'Encargado_Tienda'",
    "DROP TABLE IF EXISTS acciones_retencion",
    "ALTER TABLE roles_puesto DROP COLUMN IF EXISTS es_critico",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
