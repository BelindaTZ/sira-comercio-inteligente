"""`campanas.nombre` — nombre legible de la campaña (feature 013).

La pantalla de campañas de reactivación mostraba sólo "#123". Se agrega un
nombre opcional (las campañas del dataset Dunnhumby no lo traen).

Revision ID: 0026
Revises: 0025
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE campanas ADD COLUMN IF NOT EXISTS nombre VARCHAR(120)")


def downgrade() -> None:
    op.execute("ALTER TABLE campanas DROP COLUMN IF EXISTS nombre")
