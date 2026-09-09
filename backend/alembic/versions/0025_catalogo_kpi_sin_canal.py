"""Catálogo: quita la matriz de precios por canal y agrega el snapshot de KPIs.

1. `regla_recargo_canal` (0024) se elimina: `.specify/memory/domain-context.md`
   es explícito — SIRA es de gestión interna para tiendas físicas, "no incluye
   canal de venta en línea (...) ningún OO ni feature contempla e-commerce". La
   pantalla de Catálogo pasa a ser sólo gestión de precios y márgenes.
2. `catalogo_kpi` — una fila con los KPIs de la cabecera del Catálogo, que
   agregan sobre todo el histórico de ventas (margen bruto ponderado, huella
   promocional). Los refresca un job periódico (`refrescar_catalogo_kpi`),
   no se calculan por request. Mismo criterio que los KPIs de los dashboards
   de la feature 009.

Revision ID: 0025
Revises: 0024
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    """DELETE FROM role_permisos_tabla
       WHERE nombre_tabla = 'regla_recargo_canal'
         AND modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Comercial')""",
    "DROP TABLE IF EXISTS regla_recargo_canal",
    """CREATE TABLE IF NOT EXISTS catalogo_kpi (
        id                        SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
        total_activos             INTEGER NOT NULL DEFAULT 0,
        total                     INTEGER NOT NULL DEFAULT 0,
        con_ean                   INTEGER NOT NULL DEFAULT 0,
        nuevos_30d                INTEGER NOT NULL DEFAULT 0,
        skus_con_elasticidad      INTEGER NOT NULL DEFAULT 0,
        promos_vigentes           INTEGER NOT NULL DEFAULT 0,
        skus_bajo_margen          INTEGER NOT NULL DEFAULT 0,
        margen_bruto_ponderado_pct NUMERIC(6,2),
        calculado_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DROP TABLE IF EXISTS catalogo_kpi",
    """CREATE TABLE IF NOT EXISTS regla_recargo_canal (
        canal       VARCHAR(30) PRIMARY KEY,
        nombre      VARCHAR(60) NOT NULL,
        markup_pct  NUMERIC(5,2) NOT NULL DEFAULT 0,
        descripcion TEXT,
        activo      BOOLEAN NOT NULL DEFAULT true,
        orden       SMALLINT NOT NULL DEFAULT 0,
        updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
