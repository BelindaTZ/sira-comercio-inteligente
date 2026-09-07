"""Feature 002 — clientes y fidelización: extensiones de esquema + RBAC

Top-up idempotente de los bloques "EXTENSIÓN — Feature 002" de
`01_operativo_postgres.sql` (rondas 1 y 2 de la spec 002). Un DB creado desde
cero ya los trae vía la migración 0001; esta migración los aplica sobre un DB
que se quedó en 0005 sin ellos. Cada sentencia es no-op si ya se aplicó.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-06

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    # --- ronda 1: consentimiento de datos (FR-001) y severidad de churn (FR-010) ---
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS consentimiento_datos "
    "BOOLEAN NOT NULL DEFAULT true",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS fecha_consentimiento_datos "
    "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
    "ALTER TABLE churn_score ADD COLUMN IF NOT EXISTS severidad VARCHAR(20)",
    (
        "DO $$ BEGIN "
        "ALTER TABLE churn_score ADD CONSTRAINT churn_score_severidad_check "
        "CHECK (severidad IN ('en_riesgo','inactivo')); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ),
    # --- ronda 2: clasificación de campaña, grupo de control, uplift, cupón enviado ---
    "CREATE SEQUENCE IF NOT EXISTS campanas_campaign_id_seq START WITH 100000",
    "ALTER TABLE campanas ADD COLUMN IF NOT EXISTS categoria_sira VARCHAR(20)",
    (
        "DO $$ BEGIN "
        "ALTER TABLE campanas ADD CONSTRAINT campanas_categoria_sira_check "
        "CHECK (categoria_sira IN ('hito','reactivacion')); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ),
    "ALTER TABLE campana_cliente ADD COLUMN IF NOT EXISTS grupo VARCHAR(20)",
    (
        "DO $$ BEGIN "
        "ALTER TABLE campana_cliente ADD CONSTRAINT campana_cliente_grupo_check "
        "CHECK (grupo IN ('tratado','control')); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ),
    """CREATE TABLE IF NOT EXISTS campana_resultado (
        campaign_id INTEGER PRIMARY KEY REFERENCES campanas(campaign_id) ON DELETE CASCADE,
        tasa_retorno_tratado DECIMAL(5,4),
        tasa_retorno_control DECIMAL(5,4),
        uplift DECIMAL(5,4)
            GENERATED ALWAYS AS (tasa_retorno_tratado - tasa_retorno_control) STORED,
        decision VARCHAR(20) CHECK (decision IN ('aprobada_escalar','descartada')),
        empleado_decide_id INTEGER REFERENCES empleados(empleado_id),
        fecha_calculo DATE
    )""",
    """CREATE TABLE IF NOT EXISTS cupon_enviado (
        envio_id BIGSERIAL PRIMARY KEY,
        evento_id BIGINT REFERENCES eventos_cliente(evento_id) ON DELETE CASCADE,
        household_id INTEGER NOT NULL REFERENCES clientes(household_id) ON DELETE CASCADE,
        coupon_upc VARCHAR(20) NOT NULL,
        campaign_id INTEGER NOT NULL REFERENCES campanas(campaign_id),
        fecha_envio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        entregado BOOLEAN NOT NULL DEFAULT true
    )""",
    "CREATE INDEX IF NOT EXISTS idx_cupon_enviado_household_id ON cupon_enviado(household_id)",
    "CREATE INDEX IF NOT EXISTS idx_cupon_enviado_evento_id ON cupon_enviado(evento_id)",
    # --- RBAC del módulo Marketing_CRM: el patrón base sembró a Jefe_Marketing en
    #     clientes/campanas/etc.; faltan las tablas de CLV, churn y uplift de 002. ---
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Marketing_CRM'
       JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
       CROSS JOIN (VALUES ('cliente_clv'), ('churn_score'), ('campana_resultado'),
                           ('cupon_enviado'), ('clientes_demograficos')) AS t(tabla)
       WHERE r.nombre = 'Jefe_Marketing'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    """DELETE FROM role_permisos_tabla
       WHERE modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Marketing_CRM')
         AND nombre_tabla IN ('cliente_clv','churn_score','campana_resultado',
                              'cupon_enviado','clientes_demograficos')""",
    "DROP TABLE IF EXISTS cupon_enviado",
    "DROP TABLE IF EXISTS campana_resultado",
    "ALTER TABLE campana_cliente DROP CONSTRAINT IF EXISTS campana_cliente_grupo_check",
    "ALTER TABLE campana_cliente DROP COLUMN IF EXISTS grupo",
    "ALTER TABLE campanas DROP CONSTRAINT IF EXISTS campanas_categoria_sira_check",
    "ALTER TABLE campanas DROP COLUMN IF EXISTS categoria_sira",
    "DROP SEQUENCE IF EXISTS campanas_campaign_id_seq",
    "ALTER TABLE churn_score DROP CONSTRAINT IF EXISTS churn_score_severidad_check",
    "ALTER TABLE churn_score DROP COLUMN IF EXISTS severidad",
    "ALTER TABLE clientes DROP COLUMN IF EXISTS fecha_consentimiento_datos",
    "ALTER TABLE clientes DROP COLUMN IF EXISTS consentimiento_datos",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
