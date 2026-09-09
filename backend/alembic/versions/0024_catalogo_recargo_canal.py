"""Matriz de precios por canal — recargo automático sobre el PVP físico (001, US4).

La referencia de UI "Catálogo Maestro de Productos & Matriz de Precios" muestra el
PVP de tienda física y, al lado, el PVP de "Delivery App" (+12%) y "E-Commerce".
El modelo no tenía dónde guardar esa regla: se agrega `regla_recargo_canal`, una
fila por canal de venta con su `markup_pct` sobre el precio base.

- La edita el `Jefe_Comercial` (y el `Jefe_Operaciones`), módulo RBAC `Comercial`.
- El PVP por canal se calcula: `precio_base * (1 + markup_pct/100)`. No se guarda
  un precio por canal por producto — es una regla transversal (como en la
  referencia: "cubren automáticamente la comisión de pasarela y packaging").

Revision ID: 0024
Revises: 0023
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    """CREATE TABLE IF NOT EXISTS regla_recargo_canal (
        canal       VARCHAR(30) PRIMARY KEY,
        nombre      VARCHAR(60) NOT NULL,
        markup_pct  NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (markup_pct >= 0 AND markup_pct <= 100),
        descripcion TEXT,
        activo      BOOLEAN NOT NULL DEFAULT true,
        orden       SMALLINT NOT NULL DEFAULT 0,
        updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """INSERT INTO regla_recargo_canal (canal, nombre, markup_pct, descripcion, orden) VALUES
        ('fisico', 'Tienda Física Base', 0,
         'Precio de lista en góndola. Base de cálculo del resto de canales.', 1),
        ('delivery_app', 'Canal Delivery App (Uber/Rappi)', 12,
         'Cubre la comisión de pasarela y el packaging de última milla.', 2),
        ('ecommerce', 'E-Commerce Web Retiro', 0,
         'Retiro en tienda: mismo PVP físico, sin recargo.', 3)
       ON CONFLICT (canal) DO NOTHING""",
    # Factor de sensibilidad a la demanda por categoría (0 = inelástico, 1 = muy
    # elástico) — alimenta el "Simulador de Impacto" de la referencia de UI.
    # Heurístico determinista 0.10–0.45 para que la demo muestre variedad; el job
    # de pricing (feature 003) puede afinarlo luego con datos reales.
    """UPDATE margenes_objetivo
       SET factor_sensibilidad = ROUND((0.10 + (abs(hashtext(product_category)) % 36) / 100.0)::numeric, 2)
       WHERE factor_sensibilidad IS NULL""",
    # RBAC — módulo Comercial. Jefe_Comercial y Jefe_Operaciones la ven y editan.
    """INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                        can_select, can_insert, can_update, can_delete)
       SELECT r.role_id, m.modulo_id, 'regla_recargo_canal', true, false, true, false
       FROM roles r
       JOIN modulos m ON m.nombre = 'Comercial'
       JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
       WHERE r.nombre IN ('Jefe_Comercial', 'Jefe_Operaciones', 'Gerente_General')
       ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    """DELETE FROM role_permisos_tabla
       WHERE nombre_tabla = 'regla_recargo_canal'
         AND modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Comercial')""",
    "DROP TABLE IF EXISTS regla_recargo_canal",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
