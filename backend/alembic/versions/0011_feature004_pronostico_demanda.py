"""Feature 004 — pronóstico de demanda con variables exógenas

Top-up idempotente del bloque "EXTENSIÓN — Feature 004" de
`01_operativo_postgres.sql` (data-model.md). Un DB creado desde cero ya lo trae
vía la migración 0001; esta migración lo aplica sobre un DB en 0010.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-07

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    """CREATE TABLE IF NOT EXISTS modelo_demanda (
        modelo_id BIGSERIAL PRIMARY KEY,
        fecha_entrenamiento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        metrica_precision_validacion DECIMAL(6,4),
        estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'
            CHECK (estado IN ('pendiente','aprobado','rechazado','reemplazado')),
        fecha_resolucion TIMESTAMP,
        aprobado_por INTEGER REFERENCES empleados(empleado_id),
        observaciones VARCHAR(500),
        CHECK (estado = 'pendiente'
               OR (fecha_resolucion IS NOT NULL AND aprobado_por IS NOT NULL))
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_modelo_demanda_aprobado "
    "ON modelo_demanda((estado)) WHERE estado = 'aprobado'",
    """CREATE TABLE IF NOT EXISTS pronostico_demanda (
        pronostico_id BIGSERIAL PRIMARY KEY,
        modelo_id BIGINT NOT NULL REFERENCES modelo_demanda(modelo_id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
        tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
        semana INTEGER NOT NULL CHECK (semana BETWEEN 1 AND 53),
        anio INTEGER NOT NULL,
        cantidad_pronosticada DECIMAL(10,2) NOT NULL CHECK (cantidad_pronosticada >= 0),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (modelo_id, product_id, tienda_id, semana, anio)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_pronostico_demanda_producto_tienda "
    "ON pronostico_demanda(product_id, tienda_id, semana, anio)",
    """CREATE TABLE IF NOT EXISTS monitoreo_precision_modelo (
        monitoreo_id BIGSERIAL PRIMARY KEY,
        modelo_id BIGINT NOT NULL REFERENCES modelo_demanda(modelo_id) ON DELETE CASCADE,
        semana INTEGER NOT NULL CHECK (semana BETWEEN 1 AND 53),
        anio INTEGER NOT NULL,
        metrica_precision DECIMAL(6,4) NOT NULL,
        supero_umbral_alerta BOOLEAN NOT NULL DEFAULT false,
        fecha_calculo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (modelo_id, semana, anio)
    )""",
    """CREATE TABLE IF NOT EXISTS configuracion_pronostico (
        clave VARCHAR(60) PRIMARY KEY,
        valor DECIMAL(10,4) NOT NULL,
        descripcion VARCHAR(250)
    )""",
    """INSERT INTO configuracion_pronostico (clave, valor, descripcion) VALUES
        ('precision_minima_aprobacion', 0.35, 'WAPE de validación máximo aceptable para que el Jefe de TI apruebe un modelo — referencia, no bloqueo automático (FR-002/FR-003)'),
        ('umbral_degradacion_semanal_pct', 0.45, 'WAPE semanal en producción por encima del cual se genera una alerta de degradación para el Jefe de TI (FR-012)'),
        ('historial_minimo_semanas', 12, 'Semanas mínimas de historial de ventas para incluir un producto/tienda en el entrenamiento (FR-006, research.md Decisión 6)')
       ON CONFLICT (clave) DO NOTHING""",
    "ALTER TABLE alertas_inventario ADD COLUMN IF NOT EXISTS origen_calculo "
    "VARCHAR(20) NOT NULL DEFAULT 'rotacion_reciente'",
    (
        "DO $$ BEGIN "
        "ALTER TABLE alertas_inventario ADD CONSTRAINT chk_alerta_origen_calculo "
        "CHECK (origen_calculo IN ('modelo_pronostico','rotacion_reciente')); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ),
    "ALTER TABLE orden_compra_detalle ADD COLUMN IF NOT EXISTS origen_calculo "
    "VARCHAR(20) NOT NULL DEFAULT 'rotacion_reciente'",
    (
        "DO $$ BEGIN "
        "ALTER TABLE orden_compra_detalle ADD CONSTRAINT chk_ocd_origen_calculo "
        "CHECK (origen_calculo IN ('modelo_pronostico','rotacion_reciente')); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ),
    # RBAC (T007): módulo TI cubre las tablas nuevas; Jefe_Operaciones ve eventos_quiebre_stock.
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, true
       FROM roles r, modulos m
       WHERE m.nombre = 'TI' AND r.nombre = 'Jefe_TI'
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
       FROM roles r JOIN modulos m ON m.nombre = 'TI'
       CROSS JOIN (VALUES ('modelo_demanda'), ('pronostico_demanda'),
                           ('monitoreo_precision_modelo'), ('configuracion_pronostico')) AS t(tabla)
       WHERE r.nombre = 'Jefe_TI'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'eventos_quiebre_stock', true, true, false, false
       FROM roles r JOIN modulos m ON m.nombre = 'Operaciones'
       WHERE r.nombre = 'Jefe_Operaciones'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "ALTER TABLE orden_compra_detalle DROP CONSTRAINT IF EXISTS chk_ocd_origen_calculo",
    "ALTER TABLE orden_compra_detalle DROP COLUMN IF EXISTS origen_calculo",
    "ALTER TABLE alertas_inventario DROP CONSTRAINT IF EXISTS chk_alerta_origen_calculo",
    "ALTER TABLE alertas_inventario DROP COLUMN IF EXISTS origen_calculo",
    "DROP TABLE IF EXISTS monitoreo_precision_modelo",
    "DROP TABLE IF EXISTS pronostico_demanda",
    "DROP TABLE IF EXISTS configuracion_pronostico",
    "DROP TABLE IF EXISTS modelo_demanda",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
