"""Feature 010 — plataforma de datos táctico-estratégica

Top-up idempotente del bloque "EXTENSIÓN — Feature 010" de
`01_operativo_postgres.sql` (data-model.md). Aplica sobre un DB en 0017.

Crea las 4 tablas de CONTROL del pipeline ELT en PostgreSQL (Principio II/III —
el resultado de cada corrida es un registro real, no un estado en memoria de
Airflow; los datos de negocio del warehouse viven sólo en ClickHouse):

- `modelo_datos_warehouse` — catálogo del modelo único (FR-001).
- `corrida_carga` — una fila por corrida de una entidad, con el índice único
  parcial de exclusión mutua por destino (`uq_corrida_carga_en_progreso`, FR-005)
  y el índice de listado.
- `registro_calidad_carga` — registros señalados por incumplir una regla mínima
  de calidad, sin bloquear el resto del lote (FR-007).
- `politica_gobierno_datos` — documento append-only (FR-009/FR-010).

RBAC: sin rol ni módulo nuevo. `Jefe_TI` ya tiene el módulo `TI` desde 0011;
esta migración le agrega el permiso de tabla sobre las 4 tablas nuevas
(data-model.md §RBAC).

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    # ---- modelo_datos_warehouse (FR-001, research.md Decisión 1) ----
    """CREATE TABLE IF NOT EXISTS modelo_datos_warehouse (
        entidad_id SERIAL PRIMARY KEY,
        nombre_entidad VARCHAR(60) NOT NULL UNIQUE,
        tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('fact','dimension')),
        tabla_origen_postgres VARCHAR(60) NOT NULL,
        descripcion TEXT,
        activa BOOLEAN NOT NULL DEFAULT true,
        definido_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
        fecha_definicion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    # ---- corrida_carga (FR-002 a FR-006, FR-012, research.md Decisiones 2/3) ----
    """CREATE TABLE IF NOT EXISTS corrida_carga (
        corrida_id BIGSERIAL PRIMARY KEY,
        entidad_id INTEGER NOT NULL REFERENCES modelo_datos_warehouse(entidad_id),
        tipo_carga VARCHAR(12) NOT NULL CHECK (tipo_carga IN ('completa','incremental')),
        origen VARCHAR(20) NOT NULL CHECK (origen IN ('postgres','minio_landing_zone')),
        estado VARCHAR(12) NOT NULL DEFAULT 'en_progreso'
            CHECK (estado IN ('en_progreso','exitosa','fallida')),
        filas_cargadas INTEGER,
        filas_error INTEGER NOT NULL DEFAULT 0,
        fecha_inicio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        fecha_fin TIMESTAMP,
        CONSTRAINT chk_corrida_carga_fin CHECK (estado = 'en_progreso' OR fecha_fin IS NOT NULL),
        CONSTRAINT chk_corrida_carga_filas
            CHECK (estado <> 'exitosa' OR filas_cargadas IS NOT NULL)
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_corrida_carga_en_progreso "
    "ON corrida_carga(entidad_id) WHERE estado = 'en_progreso'",
    "CREATE INDEX IF NOT EXISTS idx_corrida_carga_entidad_fecha "
    "ON corrida_carga(entidad_id, fecha_inicio DESC)",
    # ---- registro_calidad_carga (FR-007, research.md Decisión 4) ----
    """CREATE TABLE IF NOT EXISTS registro_calidad_carga (
        registro_id BIGSERIAL PRIMARY KEY,
        corrida_id BIGINT NOT NULL REFERENCES corrida_carga(corrida_id) ON DELETE CASCADE,
        descripcion_problema VARCHAR(300) NOT NULL,
        identificador_registro VARCHAR(100),
        fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS idx_registro_calidad_carga_corrida "
    "ON registro_calidad_carga(corrida_id)",
    # ---- politica_gobierno_datos (FR-009/FR-010, research.md Decisión 5 — append-only) ----
    """CREATE TABLE IF NOT EXISTS politica_gobierno_datos (
        politica_id BIGSERIAL PRIMARY KEY,
        texto TEXT NOT NULL,
        definido_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    # ---- RBAC — `Jefe_TI` sobre el módulo `TI` ya reservado (data-model.md §RBAC) ----
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, true
       FROM roles r, modulos m
       WHERE m.nombre = 'TI' AND r.nombre = 'Jefe_TI'
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, t.ins, t.upd, false
       FROM roles r JOIN modulos m ON m.nombre = 'TI'
       CROSS JOIN (VALUES
            ('modelo_datos_warehouse', true, true),
            ('corrida_carga', false, false),
            ('registro_calidad_carga', false, false),
            ('politica_gobierno_datos', true, false)
       ) AS t(tabla, ins, upd)
       WHERE r.nombre = 'Jefe_TI'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DELETE FROM role_permisos_tabla rpt USING roles r, modulos m "
    "WHERE rpt.role_id = r.role_id AND rpt.modulo_id = m.modulo_id AND m.nombre = 'TI' "
    "AND r.nombre = 'Jefe_TI' AND rpt.nombre_tabla IN "
    "('modelo_datos_warehouse','corrida_carga','registro_calidad_carga','politica_gobierno_datos')",
    "DROP TABLE IF EXISTS politica_gobierno_datos",
    "DROP TABLE IF EXISTS registro_calidad_carga",
    "DROP TABLE IF EXISTS corrida_carga",
    "DROP TABLE IF EXISTS modelo_datos_warehouse",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
