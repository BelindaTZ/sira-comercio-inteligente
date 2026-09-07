"""US1 — punto de venta: generador de venta_id, comprobante, saldo por lote

Top-up idempotente de la ronda 7 de `01_operativo_postgres.sql`. Un DB creado
desde cero ya trae estos cambios vía la migración 0001 (que reproduce el .sql
completo); esta migración los aplica sobre un DB que se quedó en 0001 sin la
ronda 7. Cada sentencia es no-op si el objeto ya existe.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-06

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Sentencias sueltas (se ejecutan una a una: asyncpg no admite multi-statement
# con dollar-quoting en una sola llamada).
UPGRADE_STATEMENTS: list[str] = [
    # FR-001: generador de venta_id para el POS (fuera del rango de basket_id sembrado)
    "CREATE SEQUENCE IF NOT EXISTS ventas_venta_id_seq AS BIGINT START WITH 100000000000",
    "ALTER TABLE ventas ALTER COLUMN venta_id SET DEFAULT nextval('ventas_venta_id_seq')",
    # FR-004 / research.md §7: clave del objeto del comprobante PDF en MinIO
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS comprobante_objeto VARCHAR(300)",
    # spec.md Key Entities: saldo vivo por lote para el descuento FIFO/FEFO (FR-005)
    "ALTER TABLE lotes ADD COLUMN IF NOT EXISTS cantidad_disponible INTEGER",
    "UPDATE lotes SET cantidad_disponible = cantidad_recibida WHERE cantidad_disponible IS NULL",
    "ALTER TABLE lotes ALTER COLUMN cantidad_disponible SET NOT NULL",
    (
        "DO $$ BEGIN "
        "ALTER TABLE lotes ADD CONSTRAINT chk_lotes_cantidad_disponible "
        "CHECK (cantidad_disponible >= 0 AND cantidad_disponible <= cantidad_recibida); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ),
    # FR-005 / FR-026: trazabilidad venta -> línea -> lote(s)
    "ALTER TABLE movimientos_inventario ADD COLUMN IF NOT EXISTS lote_id BIGINT REFERENCES lotes(lote_id)",
    "CREATE INDEX IF NOT EXISTS idx_movimientos_inventario_lote_id ON movimientos_inventario(lote_id)",
    # --- RBAC (ronda 7) ---
    # FR-001/FR-004: el cajero confirma la venta (UPDATE de ventas.estado).
    """UPDATE role_permisos_tabla SET can_update = true
       WHERE role_id = (SELECT role_id FROM roles WHERE nombre = 'Cajero')
         AND nombre_tabla = 'ventas'""",
    # FR-027/FR-007: el Encargado_Tienda autoriza remociones de línea y anula ventas.
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, true
       FROM roles r, modulos m
       WHERE r.nombre = 'Encargado_Tienda' AND m.nombre = 'Ventas'
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, (t.tabla = 'venta_detalle')
       FROM roles r
       JOIN modulos m ON m.nombre = 'Ventas'
       CROSS JOIN (VALUES ('ventas'), ('venta_detalle'), ('devoluciones')) AS t(tabla)
       WHERE r.nombre = 'Encargado_Tienda'
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    """DELETE FROM role_permisos_tabla
       WHERE role_id = (SELECT role_id FROM roles WHERE nombre = 'Encargado_Tienda')
         AND modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Ventas')""",
    """DELETE FROM role_permisos_modulo
       WHERE role_id = (SELECT role_id FROM roles WHERE nombre = 'Encargado_Tienda')
         AND modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Ventas')""",
    """UPDATE role_permisos_tabla SET can_update = false
       WHERE role_id = (SELECT role_id FROM roles WHERE nombre = 'Cajero')
         AND nombre_tabla = 'ventas'""",
    "DROP INDEX IF EXISTS idx_movimientos_inventario_lote_id",
    "ALTER TABLE movimientos_inventario DROP COLUMN IF EXISTS lote_id",
    "ALTER TABLE lotes DROP CONSTRAINT IF EXISTS chk_lotes_cantidad_disponible",
    "ALTER TABLE lotes DROP COLUMN IF EXISTS cantidad_disponible",
    "ALTER TABLE ventas DROP COLUMN IF EXISTS comprobante_objeto",
    "ALTER TABLE ventas ALTER COLUMN venta_id DROP DEFAULT",
    "DROP SEQUENCE IF EXISTS ventas_venta_id_seq",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
