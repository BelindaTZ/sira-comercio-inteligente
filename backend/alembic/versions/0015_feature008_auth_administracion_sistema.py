"""Feature 008 — autenticación y administración del sistema

Top-up idempotente del bloque "EXTENSIÓN — Feature 008" de
`01_operativo_postgres.sql`. Aplica sobre un DB en 0014.

- Crea `recuperacion_password` e `intentos_login` (data-model.md).
- Crea `fn_inhabilitar_cuenta_usuario()` + trigger `trg_inhabilitar_cuenta_baja_empleado`
  (research.md Decisión 4): dar de baja a un empleado inhabilita su cuenta, y no
  se revierte al reactivarlo.
- RBAC: primer uso de los módulos `Sistema` (Jefe_TI) y `RRHH` (Jefe_RRHH).

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    """CREATE TABLE IF NOT EXISTS recuperacion_password (
        token_id BIGSERIAL PRIMARY KEY,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(usuario_id) ON DELETE CASCADE,
        token VARCHAR(128) UNIQUE NOT NULL,
        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        fecha_expiracion TIMESTAMP NOT NULL,
        usado BOOLEAN NOT NULL DEFAULT false
    )""",
    "CREATE INDEX IF NOT EXISTS idx_recuperacion_password_usuario_id "
    "ON recuperacion_password(usuario_id)",
    """CREATE TABLE IF NOT EXISTS intentos_login (
        intento_id BIGSERIAL PRIMARY KEY,
        usuario_id INTEGER REFERENCES usuarios(usuario_id) ON DELETE SET NULL,
        username_intentado VARCHAR(50) NOT NULL,
        exitoso BOOLEAN NOT NULL,
        fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS idx_intentos_login_usuario_id ON intentos_login(usuario_id)",
    "CREATE INDEX IF NOT EXISTS idx_intentos_login_fecha_hora ON intentos_login(fecha_hora)",
    # Trigger: inhabilitación automática de cuenta al dar de baja al empleado.
    """CREATE OR REPLACE FUNCTION fn_inhabilitar_cuenta_usuario()
       RETURNS TRIGGER AS $fn$
       BEGIN
           UPDATE usuarios SET activo = false WHERE empleado_id = NEW.empleado_id;
           RETURN NEW;
       END;
       $fn$ LANGUAGE plpgsql""",
    "DROP TRIGGER IF EXISTS trg_inhabilitar_cuenta_baja_empleado ON empleados",
    """CREATE TRIGGER trg_inhabilitar_cuenta_baja_empleado
       AFTER UPDATE ON empleados
       FOR EACH ROW
       WHEN (NEW.activo = false AND OLD.activo = true)
       EXECUTE FUNCTION fn_inhabilitar_cuenta_usuario()""",
    # RBAC — Jefe_TI → Sistema (primer uso del módulo).
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, true
       FROM roles r, modulos m
       WHERE m.nombre = 'Sistema' AND r.nombre = 'Jefe_TI'
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, t.w, t.w, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Sistema'
       CROSS JOIN (VALUES
            ('usuarios', true),
            ('role_permisos_modulo', true),
            ('role_permisos_tabla', true),
            ('recuperacion_password', false),
            ('intentos_login', false),
            ('auditoria_log', false)
       ) AS t(tabla, w)
       WHERE r.nombre = 'Jefe_TI'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    # RBAC — Jefe_RRHH → RRHH (primer uso del módulo).
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, true
       FROM roles r, modulos m
       WHERE m.nombre = 'RRHH' AND r.nombre = 'Jefe_RRHH'
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'empleados', true, true, true, false
       FROM roles r JOIN modulos m ON m.nombre = 'RRHH'
       WHERE r.nombre = 'Jefe_RRHH'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DROP TRIGGER IF EXISTS trg_inhabilitar_cuenta_baja_empleado ON empleados",
    "DROP FUNCTION IF EXISTS fn_inhabilitar_cuenta_usuario()",
    "DELETE FROM role_permisos_tabla rpt USING roles r, modulos m "
    "WHERE rpt.role_id = r.role_id AND rpt.modulo_id = m.modulo_id "
    "AND ((m.nombre = 'Sistema' AND r.nombre = 'Jefe_TI') "
    "     OR (m.nombre = 'RRHH' AND r.nombre = 'Jefe_RRHH'))",
    "DELETE FROM role_permisos_modulo rpm USING roles r, modulos m "
    "WHERE rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id "
    "AND ((m.nombre = 'Sistema' AND r.nombre = 'Jefe_TI') "
    "     OR (m.nombre = 'RRHH' AND r.nombre = 'Jefe_RRHH'))",
    "DROP TABLE IF EXISTS intentos_login",
    "DROP TABLE IF EXISTS recuperacion_password",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
