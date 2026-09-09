"""Trazabilidad de auditoría en ajustes y mermas (001, US2 — feature 013).

Los modales de "Ajuste de Conteo Físico & Corrección de Stock" y "Declarar &
Registrar Merma" (docs/diseno-ui) piden un motivo y una justificación. El
esquema base sólo guardaba las cantidades y, en merma, la `causa`. Se agregan
columnas aditivas y opcionales (no rompen inserts existentes):

- `ajustes_inventario.motivo`        — causal del descuadre (texto corto)
- `ajustes_inventario.observaciones` — justificación libre de auditoría
- `mermas.destino`                   — destino físico de las unidades dadas de baja
- `mermas.observaciones`             — detalle del siniestro / evidencia

Revision ID: 0022
Revises: 0021
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    "ALTER TABLE ajustes_inventario ADD COLUMN IF NOT EXISTS motivo VARCHAR(30)",
    "ALTER TABLE ajustes_inventario ADD COLUMN IF NOT EXISTS observaciones TEXT",
    "ALTER TABLE mermas ADD COLUMN IF NOT EXISTS destino VARCHAR(30)",
    "ALTER TABLE mermas ADD COLUMN IF NOT EXISTS observaciones TEXT",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "ALTER TABLE mermas DROP COLUMN IF EXISTS observaciones",
    "ALTER TABLE mermas DROP COLUMN IF EXISTS destino",
    "ALTER TABLE ajustes_inventario DROP COLUMN IF EXISTS observaciones",
    "ALTER TABLE ajustes_inventario DROP COLUMN IF EXISTS motivo",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
