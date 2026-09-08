"""Feature 007 — pagos y seguridad

Top-up idempotente del bloque "EXTENSIÓN — Feature 007" de
`01_operativo_postgres.sql` (data-model.md). Aplica sobre un DB en 0013.

- Extiende aditivamente `medios_pago` (aprobación/baja) y `ventas`
  (`fecha_inicio_cobro`, nullable — solo ventas registradas en vivo, Principio VII).
- Crea `incidente_seguridad_pago` (independiente de `incidentes_fraude` de 006) y
  `politica_seguridad_pagos` (append-only, mismo criterio que `protocolo_escalamiento`).
- RBAC: sin rol ni módulo nuevo. `Jefe_TI` y `Jefe_Comercial` reciben acceso al
  módulo `Ventas` (medios de pago / reporte de tiempo de cobro), mismo patrón que
  `Jefe_Marketing`→`Ventas` en 005.

Nota de nomenclatura: 006 fijó el módulo backend como `modules/caja/` (no
`finanzas/`) y el prefijo de API como `/api/caja/`. Esta feature extiende
`modules/caja/` y `modules/ventas/`; los contratos que dicen `/api/finanzas/...`
se implementan bajo `/api/caja/...`.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    # ---- medios_pago: aprobación / baja (research.md Decisión 3) ----
    "ALTER TABLE medios_pago ADD COLUMN IF NOT EXISTS aprobado BOOLEAN NOT NULL DEFAULT true",
    "ALTER TABLE medios_pago ADD COLUMN IF NOT EXISTS aprobado_por "
    "INTEGER REFERENCES empleados(empleado_id)",
    "ALTER TABLE medios_pago ADD COLUMN IF NOT EXISTS fecha_aprobacion TIMESTAMP",
    "ALTER TABLE medios_pago ADD COLUMN IF NOT EXISTS fecha_baja TIMESTAMP",
    # ---- ventas: marca de inicio de cobro (research.md Decisión 6/7) ----
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS fecha_inicio_cobro TIMESTAMP",
    "CREATE INDEX IF NOT EXISTS idx_ventas_fecha_inicio_cobro "
    "ON ventas(fecha_inicio_cobro) WHERE fecha_inicio_cobro IS NOT NULL",
    # ---- incidente_seguridad_pago (independiente de incidentes_fraude, Decisión 4) ----
    """CREATE TABLE IF NOT EXISTS incidente_seguridad_pago (
        incidente_seguridad_id BIGSERIAL PRIMARY KEY,
        datafono_id INTEGER REFERENCES datafonos(datafono_id),
        registrado_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
        descripcion TEXT NOT NULL,
        estado VARCHAR(20) NOT NULL DEFAULT 'abierto'
            CHECK (estado IN ('abierto','en_investigacion','cerrado')),
        actualizado_por INTEGER REFERENCES empleados(empleado_id),
        fecha_actualizacion TIMESTAMP,
        fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS idx_incidente_seguridad_pago_estado "
    "ON incidente_seguridad_pago(estado)",
    "CREATE INDEX IF NOT EXISTS idx_incidente_seguridad_pago_fecha "
    "ON incidente_seguridad_pago(fecha_hora)",
    # ---- politica_seguridad_pagos (append-only, Decisión 5) ----
    """CREATE TABLE IF NOT EXISTS politica_seguridad_pagos (
        politica_id BIGSERIAL PRIMARY KEY,
        texto TEXT NOT NULL,
        definido_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS idx_politica_seguridad_pagos_fecha_creacion "
    "ON politica_seguridad_pagos(fecha_creacion DESC)",
    # ---- Seed inicial de política vigente (best-effort: sólo si hay empleados) ----
    """INSERT INTO politica_seguridad_pagos (texto, definido_por)
       SELECT 'Política de seguridad de pagos (versión inicial). Lineamientos: '
              '1) todo datáfono debe cumplir la versión mínima de firmware vigente antes de operar; '
              '2) no se almacenan datos completos de tarjeta en ningún sistema propio; '
              '3) todo incidente de seguridad de pago se registra y se investiga hasta cerrarse; '
              '4) sólo se ofrecen en caja los medios de pago aprobados por el Jefe de TI.',
              empleado_id FROM empleados ORDER BY empleado_id LIMIT 1""",
    # ---- RBAC (T004) — sin rol ni módulo nuevo ----
    # Jefe_TI y Jefe_Comercial reciben acceso al módulo Ventas (patrón de 005).
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, (r.nombre = 'Jefe_TI')
       FROM roles r, modulos m
       WHERE m.nombre = 'Ventas' AND r.nombre IN ('Jefe_TI','Jefe_Comercial')
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    # Módulo Ventas: Jefe_TI administra medios_pago; Jefe_Comercial lee ventas.
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'medios_pago', true, true, true, false
       FROM roles r JOIN modulos m ON m.nombre = 'Ventas'
       WHERE r.nombre = 'Jefe_TI'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'ventas', true, false, false, false
       FROM roles r JOIN modulos m ON m.nombre = 'Ventas'
       WHERE r.nombre = 'Jefe_Comercial'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    # Módulo Finanzas (ya sembrado desde 006): tablas nuevas + disponibilidad de datáfono.
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, t.sel, t.ins, t.upd, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Finanzas'
       CROSS JOIN (VALUES
            ('datafonos', true, false, true),
            ('politica_seguridad_pagos', true, false, false)
       ) AS t(tabla, sel, ins, upd)
       WHERE r.nombre = 'Encargado_Tienda'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, t.ins, t.ins, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Finanzas'
       CROSS JOIN (VALUES
            ('incidente_seguridad_pago', true),
            ('politica_seguridad_pagos', true)
       ) AS t(tabla, ins)
       WHERE r.nombre = 'Jefe_TI'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, false, false, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Finanzas'
       CROSS JOIN (VALUES ('incidente_seguridad_pago'), ('politica_seguridad_pagos')) AS t(tabla)
       WHERE r.nombre = 'Jefe_Finanzas'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DELETE FROM role_permisos_tabla rpt USING modulos m "
    "WHERE rpt.modulo_id = m.modulo_id AND m.nombre = 'Finanzas' "
    "AND rpt.nombre_tabla IN ('incidente_seguridad_pago','politica_seguridad_pagos')",
    "DELETE FROM role_permisos_tabla rpt USING roles r, modulos m "
    "WHERE rpt.role_id = r.role_id AND rpt.modulo_id = m.modulo_id AND m.nombre = 'Finanzas' "
    "AND r.nombre = 'Encargado_Tienda' AND rpt.nombre_tabla = 'datafonos'",
    "DELETE FROM role_permisos_tabla rpt USING roles r, modulos m "
    "WHERE rpt.role_id = r.role_id AND rpt.modulo_id = m.modulo_id AND m.nombre = 'Ventas' "
    "AND ((r.nombre = 'Jefe_TI' AND rpt.nombre_tabla = 'medios_pago') "
    "     OR (r.nombre = 'Jefe_Comercial' AND rpt.nombre_tabla = 'ventas'))",
    "DELETE FROM role_permisos_modulo rpm USING roles r, modulos m "
    "WHERE rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id AND m.nombre = 'Ventas' "
    "AND r.nombre IN ('Jefe_TI','Jefe_Comercial')",
    "DROP TABLE IF EXISTS politica_seguridad_pagos",
    "DROP TABLE IF EXISTS incidente_seguridad_pago",
    "DROP INDEX IF EXISTS idx_ventas_fecha_inicio_cobro",
    "ALTER TABLE ventas DROP COLUMN IF EXISTS fecha_inicio_cobro",
    "ALTER TABLE medios_pago DROP COLUMN IF EXISTS fecha_baja",
    "ALTER TABLE medios_pago DROP COLUMN IF EXISTS fecha_aprobacion",
    "ALTER TABLE medios_pago DROP COLUMN IF EXISTS aprobado_por",
    "ALTER TABLE medios_pago DROP COLUMN IF EXISTS aprobado",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
