"""Feature 002 — Ronda 6: niveles de fidelización por defecto

`niveles_fidelizacion` estaba vacía en el esquema base. El CLV compuesto de
US2 es un score 0..1 (research.md §1), así que los umbrales van en esa escala.
El Jefe de Marketing los ajusta después vía `PATCH` (FR-007). Idempotente.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-07

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    """INSERT INTO niveles_fidelizacion (nombre, umbral_clv_min) VALUES
        ('Bronce', 0.00),
        ('Plata', 0.40),
        ('Oro', 0.70),
        ('Platino', 0.90)
       ON CONFLICT (nombre) DO NOTHING""",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DELETE FROM niveles_fidelizacion WHERE nombre IN ('Bronce','Plata','Oro','Platino')",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
