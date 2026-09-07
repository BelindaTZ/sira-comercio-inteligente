"""Feature 003 — precios, márgenes y comparación de competencia

Top-up idempotente del bloque "EXTENSIÓN — Feature 003" de
`01_operativo_postgres.sql` (data-model.md). Un DB creado desde cero ya lo trae
vía la migración 0001; esta migración lo aplica sobre un DB que se quedó en 0009.
Cada sentencia es no-op si ya se aplicó.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-07

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    # --- FR-004: factor de sensibilidad por categoría ---
    "ALTER TABLE margenes_objetivo ADD COLUMN IF NOT EXISTS factor_sensibilidad DECIMAL(4,2)",
    (
        "DO $$ BEGIN "
        "ALTER TABLE margenes_objetivo ADD CONSTRAINT margenes_objetivo_factor_sensibilidad_check "
        "CHECK (factor_sensibilidad IS NULL OR factor_sensibilidad BETWEEN 0 AND 1); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ),
    # --- FR-005/FR-006: propuestas de ajuste de precio ---
    """CREATE TABLE IF NOT EXISTS propuesta_ajuste_precio (
        propuesta_id BIGSERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
        precio_actual DECIMAL(10,2) NOT NULL CHECK (precio_actual >= 0),
        precio_propuesto DECIMAL(10,2) NOT NULL CHECK (precio_propuesto >= 0),
        margen_esperado_pct DECIMAL(5,2) NOT NULL,
        estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'
            CHECK (estado IN ('pendiente','aprobada','rechazada')),
        fecha_generada TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        fecha_resolucion TIMESTAMP,
        aprobado_por INTEGER REFERENCES empleados(empleado_id),
        CHECK (estado = 'pendiente' OR (fecha_resolucion IS NOT NULL AND aprobado_por IS NOT NULL))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_propuesta_ajuste_precio_product_id "
    "ON propuesta_ajuste_precio(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_propuesta_ajuste_precio_estado "
    "ON propuesta_ajuste_precio(estado) WHERE estado = 'pendiente'",
    # --- FR-009/FR-010: descuento manual autorizado + margen real por línea ---
    "ALTER TABLE venta_detalle ADD COLUMN IF NOT EXISTS motivo_descuento VARCHAR(200)",
    "ALTER TABLE venta_detalle ADD COLUMN IF NOT EXISTS empleado_aplica_id "
    "INTEGER REFERENCES empleados(empleado_id)",
    "ALTER TABLE venta_detalle ADD COLUMN IF NOT EXISTS empleado_autoriza_id "
    "INTEGER REFERENCES empleados(empleado_id)",
    "ALTER TABLE venta_detalle ADD COLUMN IF NOT EXISTS margen_real DECIMAL(10,2)",
    "ALTER TABLE venta_detalle ADD COLUMN IF NOT EXISTS margen_bajo_minimo "
    "BOOLEAN NOT NULL DEFAULT false",
    (
        "DO $$ BEGIN "
        "ALTER TABLE venta_detalle ADD CONSTRAINT chk_venta_detalle_autorizacion_descuento CHECK ("
        "(empleado_aplica_id IS NULL AND empleado_autoriza_id IS NULL) OR "
        "(empleado_aplica_id IS NOT NULL AND empleado_autoriza_id IS NOT NULL "
        "AND empleado_aplica_id <> empleado_autoriza_id)); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ),
    # --- FR-012: revisión de margen bajo ---
    """CREATE TABLE IF NOT EXISTS revision_margen_bajo (
        revision_id BIGSERIAL PRIMARY KEY,
        venta_detalle_id BIGINT NOT NULL UNIQUE
            REFERENCES venta_detalle(venta_detalle_id) ON DELETE CASCADE,
        revisado_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
        accion_correctiva VARCHAR(500) NOT NULL,
        fecha_revision TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    # --- FR-014: competidores + precio de referencia de competencia ---
    """CREATE TABLE IF NOT EXISTS competidores (
        competidor_id SERIAL PRIMARY KEY,
        nombre VARCHAR(120) NOT NULL,
        tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('supermercado','tienda_barrio','tienda_digital')),
        ciudad VARCHAR(100)
    )""",
    """CREATE TABLE IF NOT EXISTS precio_competencia (
        precio_competencia_id BIGSERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
        competidor_id INTEGER REFERENCES competidores(competidor_id),
        tienda_id INTEGER REFERENCES tiendas(tienda_id),
        precio DECIMAL(10,2) NOT NULL CHECK (precio >= 0),
        fecha_captura DATE NOT NULL DEFAULT CURRENT_DATE,
        es_promocional BOOLEAN NOT NULL DEFAULT false,
        fuente_captura VARCHAR(20) NOT NULL DEFAULT 'manual'
            CHECK (fuente_captura IN ('manual','open_prices','sintetico')),
        registrado_por INTEGER REFERENCES empleados(empleado_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_precio_competencia_product_id "
    "ON precio_competencia(product_id)",
    # --- configuración clave/valor (3 filas iniciales) ---
    """CREATE TABLE IF NOT EXISTS configuracion_pricing (
        clave VARCHAR(60) PRIMARY KEY,
        valor DECIMAL(10,4) NOT NULL,
        descripcion VARCHAR(250)
    )""",
    """INSERT INTO configuracion_pricing (clave, valor, descripcion) VALUES
        ('margen_minimo_global_pct', 5.0, 'Piso de respaldo del margen objetivo efectivo cuando una categoría no tiene margen objetivo definido, o cuando el modificador ancla/nicho lo dejaría por debajo de este valor (Edge Case spec.md, FR-007)'),
        ('tolerancia_ajuste_pp', 2.0, 'Desviación mínima en puntos porcentuales para generar una propuesta de ajuste de precio (research.md #2, FR-005)'),
        ('umbral_alerta_competencia_pct', 5.0, 'Desviación mínima frente al precio de competencia para generar una alerta semanal (FR-016)')
       ON CONFLICT (clave) DO NOTHING""",
    # --- RBAC (T008): módulo Comercial cubre las tablas nuevas; Cajero/Encargado
    #     pueden actualizar venta_detalle (descuento manual dentro del módulo Ventas). ---
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Comercial'
       JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
       CROSS JOIN (VALUES ('margenes_objetivo'), ('propuesta_ajuste_precio'),
                           ('historial_precios'), ('revision_margen_bajo'),
                           ('competidores'), ('precio_competencia'),
                           ('configuracion_pricing')) AS t(tabla)
       WHERE r.nombre IN ('Jefe_Comercial','Jefe_Operaciones')
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    # FR-011/FR-012: el Encargado_Tienda ve y cierra el listado diario de margen bajo de SU tienda.
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, true
       FROM roles r, modulos m
       WHERE r.nombre = 'Encargado_Tienda' AND m.nombre = 'Comercial'
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'revision_margen_bajo', true, true, true, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Comercial'
       WHERE r.nombre = 'Encargado_Tienda'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    """UPDATE role_permisos_tabla SET can_update = true
       WHERE nombre_tabla = 'venta_detalle'
         AND modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Ventas')
         AND role_id IN (SELECT role_id FROM roles WHERE nombre IN ('Cajero','Encargado_Tienda'))""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DROP TABLE IF EXISTS precio_competencia",
    "DROP TABLE IF EXISTS competidores",
    "DROP TABLE IF EXISTS revision_margen_bajo",
    "DROP TABLE IF EXISTS configuracion_pricing",
    "DROP TABLE IF EXISTS propuesta_ajuste_precio",
    "ALTER TABLE venta_detalle DROP CONSTRAINT IF EXISTS chk_venta_detalle_autorizacion_descuento",
    "ALTER TABLE venta_detalle DROP COLUMN IF EXISTS margen_bajo_minimo",
    "ALTER TABLE venta_detalle DROP COLUMN IF EXISTS margen_real",
    "ALTER TABLE venta_detalle DROP COLUMN IF EXISTS empleado_autoriza_id",
    "ALTER TABLE venta_detalle DROP COLUMN IF EXISTS empleado_aplica_id",
    "ALTER TABLE venta_detalle DROP COLUMN IF EXISTS motivo_descuento",
    "ALTER TABLE margenes_objetivo DROP CONSTRAINT IF EXISTS "
    "margenes_objetivo_factor_sensibilidad_check",
    "ALTER TABLE margenes_objetivo DROP COLUMN IF EXISTS factor_sensibilidad",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
