"""Feature 012 — traslados de stock entre tiendas

Top-up idempotente del bloque "EXTENSIÓN — Feature 012" de
`01_operativo_postgres.sql` (data-model.md). Aplica sobre un DB en 0016.

- Extiende el CHECK de `traslados_stock.estado` para incluir `'rechazado'`
  (research.md Decisión 1).
- Agrega columnas de trazabilidad por transición (`resuelto_por`,
  `fecha_resolucion`, `recibido_por`, `fecha_recepcion`, `fecha_cancelacion`)
  con sus CHECK de consistencia (research.md Decisión 2, FR-011).
- Crea los 3 índices de apoyo (listado semanal FR-012, filtro por tienda).
- RBAC: sin rol ni módulo nuevo. `role_permisos_tabla` para `traslados_stock`
  bajo el módulo `Operaciones` ya reservado — `Jefe_Operaciones` (toda la red) y
  `Encargado_Tienda` (alcance a su tienda, validado en la capa de servicio).

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    # ---- estado: + 'rechazado' (research.md Decisión 1) ----
    "ALTER TABLE traslados_stock DROP CONSTRAINT IF EXISTS traslados_stock_estado_check",
    """ALTER TABLE traslados_stock ADD CONSTRAINT traslados_stock_estado_check
       CHECK (estado IN ('solicitado','en_transito','recibido','cancelado','rechazado'))""",
    # ---- columnas de trazabilidad por transición (research.md Decisión 2) ----
    "ALTER TABLE traslados_stock ADD COLUMN IF NOT EXISTS resuelto_por "
    "INTEGER REFERENCES empleados(empleado_id)",
    "ALTER TABLE traslados_stock ADD COLUMN IF NOT EXISTS fecha_resolucion TIMESTAMP",
    "ALTER TABLE traslados_stock ADD COLUMN IF NOT EXISTS recibido_por "
    "INTEGER REFERENCES empleados(empleado_id)",
    "ALTER TABLE traslados_stock ADD COLUMN IF NOT EXISTS fecha_recepcion TIMESTAMP",
    "ALTER TABLE traslados_stock ADD COLUMN IF NOT EXISTS fecha_cancelacion TIMESTAMP",
    "ALTER TABLE traslados_stock DROP CONSTRAINT IF EXISTS chk_traslados_stock_resolucion",
    """ALTER TABLE traslados_stock ADD CONSTRAINT chk_traslados_stock_resolucion
       CHECK (estado NOT IN ('en_transito','recibido','rechazado')
              OR (resuelto_por IS NOT NULL AND fecha_resolucion IS NOT NULL))""",
    "ALTER TABLE traslados_stock DROP CONSTRAINT IF EXISTS chk_traslados_stock_recepcion",
    """ALTER TABLE traslados_stock ADD CONSTRAINT chk_traslados_stock_recepcion
       CHECK (estado <> 'recibido' OR (recibido_por IS NOT NULL AND fecha_recepcion IS NOT NULL))""",
    # ---- índices (research.md Decisión 2 / FR-012) ----
    "CREATE INDEX IF NOT EXISTS idx_traslados_stock_estado ON traslados_stock(estado) "
    "WHERE estado IN ('solicitado','en_transito')",
    "CREATE INDEX IF NOT EXISTS idx_traslados_stock_tienda_origen "
    "ON traslados_stock(tienda_origen_id, estado)",
    "CREATE INDEX IF NOT EXISTS idx_traslados_stock_tienda_destino "
    "ON traslados_stock(tienda_destino_id, estado)",
    # ---- RBAC — `traslados_stock` bajo el módulo `Operaciones` (data-model.md §RBAC) ----
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'traslados_stock', true, true, true, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Operaciones'
       JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
       WHERE r.nombre IN ('Jefe_Operaciones','Encargado_Tienda')
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DELETE FROM role_permisos_tabla rpt USING modulos m "
    "WHERE rpt.modulo_id = m.modulo_id AND m.nombre = 'Operaciones' "
    "AND rpt.nombre_tabla = 'traslados_stock'",
    "DROP INDEX IF EXISTS idx_traslados_stock_tienda_destino",
    "DROP INDEX IF EXISTS idx_traslados_stock_tienda_origen",
    "DROP INDEX IF EXISTS idx_traslados_stock_estado",
    "ALTER TABLE traslados_stock DROP CONSTRAINT IF EXISTS chk_traslados_stock_recepcion",
    "ALTER TABLE traslados_stock DROP CONSTRAINT IF EXISTS chk_traslados_stock_resolucion",
    "ALTER TABLE traslados_stock DROP COLUMN IF EXISTS fecha_cancelacion",
    "ALTER TABLE traslados_stock DROP COLUMN IF EXISTS fecha_recepcion",
    "ALTER TABLE traslados_stock DROP COLUMN IF EXISTS recibido_por",
    "ALTER TABLE traslados_stock DROP COLUMN IF EXISTS fecha_resolucion",
    "ALTER TABLE traslados_stock DROP COLUMN IF EXISTS resuelto_por",
    "UPDATE traslados_stock SET estado = 'cancelado' WHERE estado = 'rechazado'",
    "ALTER TABLE traslados_stock DROP CONSTRAINT IF EXISTS traslados_stock_estado_check",
    """ALTER TABLE traslados_stock ADD CONSTRAINT traslados_stock_estado_check
       CHECK (estado IN ('solicitado','en_transito','recibido','cancelado'))""",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
