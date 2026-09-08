"""Ubicación física del producto en la tienda (001, US2 — Principio XII).

La pantalla "Gestión de Inventario & Alertas FIFO" muestra dónde está cada SKU
en sala ("Pasillo 01 · G-03", "Cámara Fría A · R-04"). El modelo no tenía dónde
guardarlo: se agrega `ubicacion_producto`, una fila por (producto, tienda).

- La mantiene quien opera la sala: `Reponedor`, `Encargado_Tienda` y
  `Jefe_Operaciones` (insert + update). Módulo RBAC `Operaciones`.
- `pasillo` es obligatorio; `gondola` y `nivel` son opcionales (no toda tienda
  usa el mismo nivel de detalle).
- PK compuesta (product_id, tienda_id): un producto ocupa una ubicación por
  tienda. Cambiarlo = update de la misma fila (histórico no requerido por spec).

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    """CREATE TABLE IF NOT EXISTS ubicacion_producto (
        product_id      INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
        tienda_id       INTEGER NOT NULL REFERENCES tiendas(tienda_id) ON DELETE CASCADE,
        pasillo         VARCHAR(40) NOT NULL,
        gondola         VARCHAR(20),
        nivel           VARCHAR(20),
        actualizado_por INTEGER REFERENCES empleados(empleado_id),
        updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (product_id, tienda_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_ubicacion_producto_tienda ON ubicacion_producto(tienda_id)",
    # RBAC — módulo Operaciones. Reponedor/Encargado/Jefe_Operaciones la editan.
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'ubicacion_producto', true, true, true, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Operaciones'
       JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
       WHERE r.nombre IN ('Reponedor','Encargado_Tienda','Jefe_Operaciones')
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    """DELETE FROM role_permisos_tabla
       WHERE nombre_tabla = 'ubicacion_producto'
         AND modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Operaciones')""",
    "DROP TABLE IF EXISTS ubicacion_producto",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
