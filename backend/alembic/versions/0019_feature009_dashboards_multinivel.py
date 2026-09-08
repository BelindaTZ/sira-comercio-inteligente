"""Feature 009 — dashboards multinivel

Top-up idempotente del bloque "EXTENSIÓN — Feature 009" de
`01_operativo_postgres.sql` (data-model.md). Aplica sobre un DB en 0018.

Crea las 3 tablas del snapshot publicado (Principio II/III — lo que el usuario
consulta es un registro real en PostgreSQL, no una vista en vivo sobre
ClickHouse):

- `registro_publicacion_dashboard` — una fila por corrida del job diario para
  cualquiera de los 3 niveles (estratégico/táctico/operativo), éxito o falla
  (FR-001/FR-004/FR-006/FR-008).
- `dashboard_kpi` — snapshot de valores ya calculados por otras features;
  `disponible = false` + `valor NULL` es el mecanismo explícito para OE-4
  (FR-002, Principio VII).
- `dashboard_operativo_estado` — `MAX(fecha_hora)` por tienda/dashboard operativo
  y bandera de disponibilidad (> 1 día → false, FR-007). El índice parcial sobre
  `disponible = false` es lo que consulta la alerta diaria del Jefe_TI.

RBAC (data-model.md §RBAC):
- `Gerente_General` — módulo `Direccion` (primer consumidor real), select sobre
  `registro_publicacion_dashboard` y `dashboard_kpi`; además select sobre
  `dashboard_kpi` en los 6 módulos con dashboard táctico (ya tiene `puede_ver`
  global por seed, faltaba la fila de tabla).
- Cada `Jefe_*` — select sobre `dashboard_kpi` en su propio módulo.
- `Jefe_TI` — además `registro_publicacion_dashboard` (insert, sólo el trigger
  manual de FR-010) y `dashboard_operativo_estado` (select, toda la red).

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    # ---- registro_publicacion_dashboard (FR-001/FR-004/FR-006/FR-008, research.md Decisión 1) ----
    """CREATE TABLE IF NOT EXISTS registro_publicacion_dashboard (
        publicacion_id BIGSERIAL PRIMARY KEY,
        tipo_dashboard VARCHAR(20) NOT NULL
            CHECK (tipo_dashboard IN ('estrategico','tactico','operativo')),
        modulo_id INTEGER REFERENCES modulos(modulo_id),
        exito BOOLEAN NOT NULL,
        detalle_error TEXT,
        fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT chk_pub_dashboard_modulo_solo_tactico
            CHECK (tipo_dashboard = 'tactico' OR modulo_id IS NULL),
        CONSTRAINT chk_pub_dashboard_tactico_con_modulo
            CHECK (tipo_dashboard <> 'tactico' OR modulo_id IS NOT NULL),
        CONSTRAINT chk_pub_dashboard_error_si_falla
            CHECK (exito OR detalle_error IS NOT NULL)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_registro_publicacion_tipo_fecha "
    "ON registro_publicacion_dashboard(tipo_dashboard, fecha_hora DESC)",
    # ---- dashboard_kpi (FR-001/FR-002/FR-004, research.md Decisión 2) ----
    """CREATE TABLE IF NOT EXISTS dashboard_kpi (
        kpi_id BIGSERIAL PRIMARY KEY,
        publicacion_id BIGINT NOT NULL
            REFERENCES registro_publicacion_dashboard(publicacion_id) ON DELETE CASCADE,
        dimension VARCHAR(60) NOT NULL,
        nombre_kpi VARCHAR(100) NOT NULL,
        valor DECIMAL(14,4),
        disponible BOOLEAN NOT NULL DEFAULT true,
        CONSTRAINT chk_dashboard_kpi_valor_si_disponible CHECK (disponible OR valor IS NULL)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_dashboard_kpi_publicacion ON dashboard_kpi(publicacion_id)",
    "CREATE INDEX IF NOT EXISTS idx_dashboard_kpi_dimension ON dashboard_kpi(dimension)",
    # ---- dashboard_operativo_estado (FR-006/FR-007, research.md Decisión 3) ----
    """CREATE TABLE IF NOT EXISTS dashboard_operativo_estado (
        estado_id BIGSERIAL PRIMARY KEY,
        publicacion_id BIGINT NOT NULL
            REFERENCES registro_publicacion_dashboard(publicacion_id) ON DELETE CASCADE,
        tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
        nombre_dashboard VARCHAR(60) NOT NULL,
        fecha_ultima_actualizacion TIMESTAMP,
        disponible BOOLEAN NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_dashboard_operativo_estado_publicacion "
    "ON dashboard_operativo_estado(publicacion_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_dashboard_operativo_estado_tienda_nombre "
    "ON dashboard_operativo_estado(publicacion_id, tienda_id, nombre_dashboard)",
    "CREATE INDEX IF NOT EXISTS idx_dashboard_operativo_estado_no_disponible "
    "ON dashboard_operativo_estado(tienda_id, nombre_dashboard) WHERE disponible = false",
    # ---- RBAC — Gerente_General sobre el módulo `Direccion` (primer uso real) ----
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, false
       FROM roles r, modulos m
       WHERE m.nombre = 'Direccion' AND r.nombre = 'Gerente_General'
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, false, false, false
       FROM roles r JOIN modulos m ON m.nombre = 'Direccion'
       CROSS JOIN (VALUES ('registro_publicacion_dashboard'), ('dashboard_kpi')) AS t(tabla)
       WHERE r.nombre = 'Gerente_General'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    # ---- RBAC — cada Jefe_* sobre `dashboard_kpi` en su propio módulo (dashboard táctico) ----
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, false
       FROM (VALUES
            ('Jefe_Comercial', 'Comercial'),
            ('Jefe_Marketing', 'Marketing_CRM'),
            ('Jefe_Operaciones', 'Operaciones'),
            ('Jefe_Finanzas', 'Finanzas'),
            ('Jefe_TI', 'TI'),
            ('Jefe_RRHH', 'RRHH')
       ) AS x(rol, modulo)
       JOIN roles r ON r.nombre = x.rol
       JOIN modulos m ON m.nombre = x.modulo
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'dashboard_kpi', true, false, false, false
       FROM (VALUES
            ('Jefe_Comercial', 'Comercial'),
            ('Jefe_Marketing', 'Marketing_CRM'),
            ('Jefe_Operaciones', 'Operaciones'),
            ('Jefe_Finanzas', 'Finanzas'),
            ('Jefe_TI', 'TI'),
            ('Jefe_RRHH', 'RRHH')
       ) AS x(rol, modulo)
       JOIN roles r ON r.nombre = x.rol
       JOIN modulos m ON m.nombre = x.modulo
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    # ---- RBAC — Gerente_General puede leer cualquier dashboard táctico (FR-005) ----
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'dashboard_kpi', true, false, false, false
       FROM roles r
       JOIN modulos m ON m.nombre IN
            ('Comercial','Marketing_CRM','Operaciones','Finanzas','TI','RRHH')
       JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
       WHERE r.nombre = 'Gerente_General'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    # ---- RBAC — Jefe_TI: verificación operativa + trigger manual (data-model.md §RBAC) ----
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, t.ins, false, false
       FROM roles r JOIN modulos m ON m.nombre = 'TI'
       JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
       CROSS JOIN (VALUES
            ('registro_publicacion_dashboard', true),
            ('dashboard_operativo_estado', false)
       ) AS t(tabla, ins)
       WHERE r.nombre = 'Jefe_TI'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DELETE FROM role_permisos_tabla rpt USING modulos m "
    "WHERE rpt.modulo_id = m.modulo_id AND ("
    "  (m.nombre = 'Direccion' AND rpt.nombre_tabla IN "
    "     ('registro_publicacion_dashboard','dashboard_kpi'))"
    "  OR (m.nombre = 'TI' AND rpt.nombre_tabla IN "
    "     ('registro_publicacion_dashboard','dashboard_operativo_estado'))"
    "  OR (m.nombre IN ('Comercial','Marketing_CRM','Operaciones','Finanzas','TI','RRHH')"
    "     AND rpt.nombre_tabla = 'dashboard_kpi')"
    ")",
    "DROP TABLE IF EXISTS dashboard_operativo_estado",
    "DROP TABLE IF EXISTS dashboard_kpi",
    "DROP TABLE IF EXISTS registro_publicacion_dashboard",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
