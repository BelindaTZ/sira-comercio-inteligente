"""US3 — alertas, quiebre alta demanda, stock máximo, anaquel, config y RBAC

Top-up idempotente de la ronda 9 de `01_operativo_postgres.sql` (un DB nuevo ya
la trae vía la migración 0001). Cada sentencia es no-op si ya se aplicó.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-06

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    # FR-038: tipo 'exceso_stock'
    "ALTER TABLE alertas_inventario DROP CONSTRAINT IF EXISTS alertas_inventario_tipo_check",
    "ALTER TABLE alertas_inventario ADD CONSTRAINT alertas_inventario_tipo_check "
    "CHECK (tipo IN ('reposicion','vencimiento','exceso_stock'))",
    # FR-043: quiebre de alta demanda
    "ALTER TABLE eventos_quiebre_stock ADD COLUMN IF NOT EXISTS es_alta_demanda "
    "BOOLEAN NOT NULL DEFAULT false",
    # FR-037: stock máximo por categoría (data-model §17)
    """CREATE TABLE IF NOT EXISTS stock_maximo_categoria (
        id BIGSERIAL PRIMARY KEY,
        product_category VARCHAR(100) NOT NULL,
        tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
        cantidad_maxima INTEGER NOT NULL CHECK (cantidad_maxima > 0),
        empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
        fecha_definicion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_stock_maximo_categoria "
    "ON stock_maximo_categoria(product_category, tienda_id)",
    # FR-042: verificación de anaquel (data-model §17.1)
    """CREATE TABLE IF NOT EXISTS verificacion_anaquel (
        id BIGSERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL REFERENCES productos(product_id),
        tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
        fecha DATE NOT NULL DEFAULT CURRENT_DATE,
        disponible BOOLEAN NOT NULL,
        empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_verificacion_anaquel_dia "
    "ON verificacion_anaquel(product_id, tienda_id, fecha)",
    # FR-016 / FR-020: parámetros configurables
    """CREATE TABLE IF NOT EXISTS configuracion_inventario (
        clave VARCHAR(60) PRIMARY KEY,
        valor DECIMAL(10,4) NOT NULL,
        descripcion VARCHAR(250)
    )""",
    """INSERT INTO configuracion_inventario (clave, valor, descripcion) VALUES
        ('lead_time_dias_default', 7, 'Días estimados entre orden y recepción (FR-020, research.md #5)'),
        ('stock_seguridad_pct', 0.20, 'Colchón de seguridad como fracción del consumo del lead time (FR-020)'),
        ('reposicion_ventana_dias', 14, 'Ventana de la media móvil de demanda diaria (FR-020)'),
        ('vencimiento_umbral_dias', 15, 'Días de anticipación para alertar un lote próximo a vencer (FR-016)')
       ON CONFLICT (clave) DO NOTHING""",
    # RBAC ronda 9
    """INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
       SELECT r.role_id, m.modulo_id, true, true
       FROM roles r, modulos m
       WHERE (m.nombre = 'Operaciones'
                AND r.nombre IN ('Reponedor','Encargado_Tienda','Jefe_Operaciones'))
          OR (m.nombre = 'Finanzas' AND r.nombre IN ('Jefe_Finanzas','Jefe_Operaciones'))
       ON CONFLICT (role_id, modulo_id) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla,
              true,
              (r.nombre <> 'Reponedor'
               OR t.tabla IN ('alertas_inventario','eventos_quiebre_stock','verificacion_anaquel')),
              (r.nombre <> 'Reponedor'),
              false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Operaciones'
       CROSS JOIN (VALUES ('alertas_inventario'), ('eventos_quiebre_stock'),
                           ('stock_maximo_categoria'), ('verificacion_anaquel'),
                           ('proveedores'), ('facturas_proveedor')) AS t(tabla)
       WHERE r.nombre IN ('Reponedor','Encargado_Tienda','Jefe_Operaciones')
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Finanzas'
       CROSS JOIN (VALUES ('facturas_proveedor'), ('pagos_proveedor')) AS t(tabla)
       WHERE r.nombre IN ('Jefe_Finanzas','Jefe_Operaciones')
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DROP TABLE IF EXISTS verificacion_anaquel",
    "DROP TABLE IF EXISTS stock_maximo_categoria",
    "DROP TABLE IF EXISTS configuracion_inventario",
    "ALTER TABLE eventos_quiebre_stock DROP COLUMN IF EXISTS es_alta_demanda",
    "ALTER TABLE alertas_inventario DROP CONSTRAINT IF EXISTS alertas_inventario_tipo_check",
    "ALTER TABLE alertas_inventario ADD CONSTRAINT alertas_inventario_tipo_check "
    "CHECK (tipo IN ('reposicion','vencimiento'))",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
