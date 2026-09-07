"""Feature 005 — promociones inteligentes (afinidad, ABC, liquidación, colocación)

Top-up idempotente del bloque "EXTENSIÓN — Feature 005" de
`01_operativo_postgres.sql` (data-model.md). Aplica sobre un DB en 0011.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-07

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    """CREATE TABLE IF NOT EXISTS regla_afinidad (
        regla_id BIGSERIAL PRIMARY KEY,
        product_id_antecedente INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
        product_id_consecuente INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
        soporte DECIMAL(8,6) NOT NULL CHECK (soporte >= 0),
        confianza DECIMAL(8,6) NOT NULL CHECK (confianza >= 0),
        lift DECIMAL(10,4),
        fecha_calculo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        estado VARCHAR(20) NOT NULL DEFAULT 'vigente'
            CHECK (estado IN ('vigente','reemplazada','desactivada')),
        desactivada_por INTEGER REFERENCES empleados(empleado_id),
        fecha_desactivacion TIMESTAMP,
        motivo_desactivacion VARCHAR(300),
        CHECK (product_id_antecedente <> product_id_consecuente),
        CHECK (estado <> 'desactivada'
               OR (desactivada_por IS NOT NULL AND fecha_desactivacion IS NOT NULL))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_regla_afinidad_antecedente "
    "ON regla_afinidad(product_id_antecedente) WHERE estado = 'vigente'",
    "ALTER TABLE campanas DROP CONSTRAINT IF EXISTS campanas_categoria_sira_check",
    "ALTER TABLE campanas ADD CONSTRAINT campanas_categoria_sira_check "
    "CHECK (categoria_sira IN ('hito','reactivacion','afinidad'))",
    "ALTER TABLE cupon_enviado ADD COLUMN IF NOT EXISTS regla_afinidad_id "
    "BIGINT REFERENCES regla_afinidad(regla_id)",
    """CREATE TABLE IF NOT EXISTS candidato_liquidacion (
        candidato_id BIGSERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
        tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
        semana INTEGER NOT NULL CHECK (semana BETWEEN 1 AND 53),
        anio INTEGER NOT NULL,
        rotacion_reciente_calculada DECIMAL(10,2) NOT NULL,
        descuento_sugerido_pct DECIMAL(5,2) NOT NULL,
        estado VARCHAR(20) NOT NULL DEFAULT 'candidato'
            CHECK (estado IN ('candidato','ejecutado')),
        fecha_ejecucion TIMESTAMP,
        ejecutado_por INTEGER REFERENCES empleados(empleado_id),
        UNIQUE (product_id, tienda_id, semana, anio),
        CHECK (estado = 'candidato'
               OR (fecha_ejecucion IS NOT NULL AND ejecutado_por IS NOT NULL))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_candidato_liquidacion_tienda_semana "
    "ON candidato_liquidacion(tienda_id, semana, anio)",
    """CREATE TABLE IF NOT EXISTS cambio_clasificacion_abc (
        cambio_id BIGSERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
        clasificacion_anterior CHAR(1),
        clasificacion_nueva CHAR(1) NOT NULL,
        fecha_calculo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS idx_cambio_clasificacion_abc_fecha "
    "ON cambio_clasificacion_abc(fecha_calculo)",
    """CREATE TABLE IF NOT EXISTS configuracion_promociones (
        clave VARCHAR(60) PRIMARY KEY,
        valor DECIMAL(12,6) NOT NULL,
        descripcion VARCHAR(250)
    )""",
    """INSERT INTO configuracion_promociones (clave, valor, descripcion) VALUES
        ('soporte_minimo_regla', 0.02, 'Soporte mínimo (fracción de tickets) para que un par de productos genere una regla de asociación (FR-001, research.md Decisión 2)'),
        ('confianza_minima_regla', 0.30, 'Confianza mínima (P(consecuente|antecedente)) para que una regla de asociación sea accionable (FR-001)'),
        ('vigencia_cupon_afinidad_dias', 30, 'Días durante los cuales un cupón de afinidad ya enviado bloquea el reenvío al mismo cliente para el mismo par (FR-007)'),
        ('rotacion_minima_liquidacion_semanal', 1.0, 'Unidades/semana por debajo de las cuales un producto categoría C en una tienda es candidato a liquidación (FR-011/FR-012)'),
        ('descuento_liquidacion_pct', 25.0, 'Descuento sugerido por defecto para la liquidación de un candidato de categoría C (FR-011)')
       ON CONFLICT (clave) DO NOTHING""",
    # RBAC (T008)
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Marketing_CRM'
       JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
       CROSS JOIN (VALUES ('regla_afinidad'), ('promociones')) AS t(tabla)
       WHERE r.nombre = 'Jefe_Marketing'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'promociones', true, true, false, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Marketing_CRM'
       JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
       WHERE r.nombre = 'Encargado_Tienda'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, true
       FROM roles r, modulos m
       WHERE m.nombre = 'Operaciones' AND r.nombre = 'Encargado_Tienda'
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Operaciones'
       CROSS JOIN (VALUES ('candidato_liquidacion'), ('configuracion_promociones'),
                           ('cambio_clasificacion_abc'), ('productos')) AS t(tabla)
       WHERE r.nombre IN ('Jefe_Operaciones','Encargado_Tienda')
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'regla_afinidad', true, false, false, false
       FROM roles r JOIN modulos m ON m.nombre = 'Ventas'
       WHERE r.nombre = 'Cajero'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "ALTER TABLE cupon_enviado DROP COLUMN IF EXISTS regla_afinidad_id",
    "DROP TABLE IF EXISTS candidato_liquidacion",
    "DROP TABLE IF EXISTS cambio_clasificacion_abc",
    "DROP TABLE IF EXISTS configuracion_promociones",
    "DROP TABLE IF EXISTS regla_afinidad",
    "ALTER TABLE campanas DROP CONSTRAINT IF EXISTS campanas_categoria_sira_check",
    "ALTER TABLE campanas ADD CONSTRAINT campanas_categoria_sira_check "
    "CHECK (categoria_sira IN ('hito','reactivacion'))",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
