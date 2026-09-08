"""Feature 006 — caja, mermas y fraude

Top-up idempotente del bloque "EXTENSIÓN — Feature 006" de
`01_operativo_postgres.sql` (data-model.md). Aplica sobre un DB en 0012.

- Puebla (sin extender su esquema) `apertura_caja`, `cierre_caja`, `datafonos`,
  reservadas desde 001.
- Extiende aditivamente `incidentes_fraude` (research.md Decisión 6): `cierre_id`
  pasa a nullable; se agregan `ajuste_id`, `acciones_tomadas`, `resultado`,
  `actualizado_por`, `fecha_actualizacion`.
- Crea `configuracion_seguridad_pagos`, `protocolo_escalamiento`,
  `umbral_merma_categoria` y `configuracion_caja`.
- RBAC: módulo `Finanzas` (ya sembrado desde 001) — sin rol ni módulo nuevo
  (research.md Decisión 10). `Jefe_TI` recibe acceso al módulo para datáfonos.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-07

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    # ---- Fix 001: `requiere_actualizacion` (22 chars) no cabía en VARCHAR(20) ----
    "ALTER TABLE datafonos ALTER COLUMN estado TYPE VARCHAR(30)",
    # ---- Extensión aditiva de incidentes_fraude (research.md Decisión 6) ----
    "ALTER TABLE incidentes_fraude ALTER COLUMN cierre_id DROP NOT NULL",
    "ALTER TABLE incidentes_fraude ADD COLUMN IF NOT EXISTS ajuste_id "
    "BIGINT REFERENCES ajustes_inventario(ajuste_id)",
    "ALTER TABLE incidentes_fraude ADD COLUMN IF NOT EXISTS acciones_tomadas TEXT",
    "ALTER TABLE incidentes_fraude ADD COLUMN IF NOT EXISTS resultado VARCHAR(20)",
    (
        "DO $$ BEGIN "
        "ALTER TABLE incidentes_fraude ADD CONSTRAINT chk_incidente_fraude_resultado "
        "CHECK (resultado IS NULL OR resultado IN ('fraude_confirmado','descartado')); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ),
    "ALTER TABLE incidentes_fraude ADD COLUMN IF NOT EXISTS actualizado_por "
    "INTEGER REFERENCES empleados(empleado_id)",
    "ALTER TABLE incidentes_fraude ADD COLUMN IF NOT EXISTS fecha_actualizacion TIMESTAMP",
    # ---- Configuración de seguridad de pagos (append-only, research.md Decisión 5) ----
    """CREATE TABLE IF NOT EXISTS configuracion_seguridad_pagos (
        config_id BIGSERIAL PRIMARY KEY,
        version_minima_firmware VARCHAR(30) NOT NULL,
        vigente_desde DATE NOT NULL DEFAULT CURRENT_DATE,
        actualizado_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS idx_config_seguridad_pagos_vigente_desde "
    "ON configuracion_seguridad_pagos(vigente_desde DESC)",
    # ---- Protocolo de escalamiento (append-only, research.md Decisión 7) ----
    """CREATE TABLE IF NOT EXISTS protocolo_escalamiento (
        protocolo_id BIGSERIAL PRIMARY KEY,
        texto TEXT NOT NULL,
        definido_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS idx_protocolo_escalamiento_fecha "
    "ON protocolo_escalamiento(fecha_creacion DESC)",
    # ---- Umbral de merma por categoría (upsert in place, research.md Decisión 8) ----
    """CREATE TABLE IF NOT EXISTS umbral_merma_categoria (
        product_category VARCHAR(100) PRIMARY KEY,
        porcentaje_umbral DECIMAL(5,2) NOT NULL CHECK (porcentaje_umbral > 0 AND porcentaje_umbral <= 100),
        definido_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
        fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    # ---- Configuración clave/valor de caja (umbral de ajuste anómalo, FR-010) ----
    """CREATE TABLE IF NOT EXISTS configuracion_caja (
        clave VARCHAR(60) PRIMARY KEY,
        valor DECIMAL(12,6) NOT NULL,
        descripcion VARCHAR(250)
    )""",
    """INSERT INTO configuracion_caja (clave, valor, descripcion) VALUES
        ('umbral_ajuste_inventario_anomalo', 10, 'Unidades (valor absoluto) a partir de las cuales un ajuste de inventario de 001 con diferencia negativa se señala en el reporte mensual de patrones (FR-010)')
       ON CONFLICT (clave) DO NOTHING""",
    # ---- Seed inicial de estado vigente (T007) — best-effort: sólo si hay empleados ----
    """INSERT INTO configuracion_seguridad_pagos (version_minima_firmware, actualizado_por)
       SELECT '1.0.0', empleado_id FROM empleados ORDER BY empleado_id LIMIT 1""",
    """INSERT INTO protocolo_escalamiento (texto, definido_por)
       SELECT 'Protocolo de escalamiento ante fraude confirmado (versión inicial). '
              'Al detectar un caso: 1) documentar la evidencia, 2) notificar al Jefe de '
              'Finanzas, 3) aplicar las acciones del protocolo vigente, 4) registrar el '
              'resultado sin acusar al empleado si la investigación no lo confirma.',
              empleado_id FROM empleados ORDER BY empleado_id LIMIT 1""",
    # ---- RBAC (T003 + T008): módulo Finanzas ya sembrado; sin rol ni módulo nuevo ----
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, true
       FROM roles r, modulos m
       WHERE m.nombre = 'Finanzas'
         AND r.nombre IN ('Encargado_Tienda','Jefe_Finanzas','Jefe_TI','Jefe_Operaciones')
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    # Encargado_Tienda: supervisa cuadres de su tienda, aplica protocolo, ve umbral/merma.
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, t.sel, t.ins, t.upd, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Finanzas'
       CROSS JOIN (VALUES
            ('apertura_caja', true, false, false),
            ('cierre_caja', true, false, false),
            ('incidentes_fraude', true, false, true),
            ('protocolo_escalamiento', true, false, false),
            ('umbral_merma_categoria', true, false, false),
            ('mermas', true, false, false),
            ('venta_detalle', true, false, false)
       ) AS t(tabla, sel, ins, upd)
       WHERE r.nombre = 'Encargado_Tienda'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    # Jefe_Finanzas: reporte de patrones, incidentes, protocolo.
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, t.sel, t.ins, t.upd, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Finanzas'
       CROSS JOIN (VALUES
            ('apertura_caja', true, false, false),
            ('cierre_caja', true, false, false),
            ('ajustes_inventario', true, false, false),
            ('configuracion_caja', true, false, true),
            ('incidentes_fraude', true, true, true),
            ('protocolo_escalamiento', true, true, false)
       ) AS t(tabla, sel, ins, upd)
       WHERE r.nombre = 'Jefe_Finanzas'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    # Jefe_TI: inventario de datáfonos y estándar de seguridad de pagos.
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Finanzas'
       CROSS JOIN (VALUES ('datafonos'), ('configuracion_seguridad_pagos')) AS t(tabla)
       WHERE r.nombre = 'Jefe_TI'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    # Jefe_Operaciones: umbral de merma por categoría.
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'umbral_merma_categoria', true, true, true, false
       FROM roles r JOIN modulos m ON m.nombre = 'Finanzas'
       WHERE r.nombre = 'Jefe_Operaciones'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    # Sólo las filas que ESTA migración agregó. NO se tocan las de `role_permisos_modulo`:
    # `Jefe_Finanzas`/`Jefe_Operaciones` sobre `Finanzas` ya existían desde 0004 y el FK
    # compuesto de `role_permisos_tabla` es ON DELETE CASCADE (borrarlas se llevaría por
    # delante los permisos de cuentas por pagar de 001).
    "DELETE FROM role_permisos_tabla WHERE modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Finanzas') "
    "AND nombre_tabla IN ('incidentes_fraude','protocolo_escalamiento','umbral_merma_categoria',"
    "'datafonos','configuracion_seguridad_pagos','configuracion_caja')",
    "DELETE FROM role_permisos_tabla rpt USING roles r, modulos m "
    "WHERE rpt.role_id = r.role_id AND rpt.modulo_id = m.modulo_id AND m.nombre = 'Finanzas' "
    "AND r.nombre = 'Encargado_Tienda' "
    "AND rpt.nombre_tabla IN ('apertura_caja','cierre_caja','mermas','venta_detalle')",
    "DELETE FROM role_permisos_tabla rpt USING roles r, modulos m "
    "WHERE rpt.role_id = r.role_id AND rpt.modulo_id = m.modulo_id AND m.nombre = 'Finanzas' "
    "AND r.nombre = 'Jefe_Finanzas' "
    "AND rpt.nombre_tabla IN ('apertura_caja','cierre_caja','ajustes_inventario')",
    "DELETE FROM role_permisos_modulo WHERE modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Finanzas') "
    "AND role_id IN (SELECT role_id FROM roles WHERE nombre IN ('Encargado_Tienda','Jefe_TI'))",
    "DROP TABLE IF EXISTS configuracion_caja",
    "DROP TABLE IF EXISTS umbral_merma_categoria",
    "DROP TABLE IF EXISTS protocolo_escalamiento",
    "DROP TABLE IF EXISTS configuracion_seguridad_pagos",
    "ALTER TABLE incidentes_fraude DROP CONSTRAINT IF EXISTS chk_incidente_fraude_resultado",
    "ALTER TABLE incidentes_fraude DROP COLUMN IF EXISTS fecha_actualizacion",
    "ALTER TABLE incidentes_fraude DROP COLUMN IF EXISTS actualizado_por",
    "ALTER TABLE incidentes_fraude DROP COLUMN IF EXISTS resultado",
    "ALTER TABLE incidentes_fraude DROP COLUMN IF EXISTS acciones_tomadas",
    "ALTER TABLE incidentes_fraude DROP COLUMN IF EXISTS ajuste_id",
    "ALTER TABLE datafonos ALTER COLUMN estado TYPE VARCHAR(20)",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
