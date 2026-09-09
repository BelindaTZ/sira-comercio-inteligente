"""Canje de puntos y aplicación de cupones en el punto de venta.

Feature 018 (extensión de 002/005): el Encargado/Cajero puede canjear los puntos
del Club Marzú del cliente y aplicar sus cupones vigentes durante una venta.

- `ventas.descuento_puntos`: monto en USD que el canje de puntos descuenta del
  total de esa venta (nivel venta, no línea).
- `canje_puntos`: libro de canjes — cada fila resta del saldo de puntos que ve el
  cliente (los puntos ganados se derivan del gasto; los canjeados se restan aquí).
- `campanas.descuento_pct`: % de descuento que aplica un cupón de esa campaña
  sobre la línea de su producto (el dataset de cupones no traía monto).

Revision ID: 0033
Revises: 0032
Create Date: 2026-09-09

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS descuento_puntos NUMERIC(12,2) "
        "NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE campanas ADD COLUMN IF NOT EXISTS descuento_pct NUMERIC(5,2) "
        "NOT NULL DEFAULT 15"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS canje_puntos (
            canje_id     BIGSERIAL PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES clientes(household_id) ON DELETE CASCADE,
            venta_id     BIGINT  NOT NULL REFERENCES ventas(venta_id) ON DELETE CASCADE,
            puntos       INTEGER NOT NULL CHECK (puntos > 0),
            valor_usd    NUMERIC(12,2) NOT NULL CHECK (valor_usd > 0),
            fecha_hora   TIMESTAMP NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_canje_puntos_household ON canje_puntos(household_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_canje_puntos_venta ON canje_puntos(venta_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS canje_puntos")
    op.execute("ALTER TABLE campanas DROP COLUMN IF EXISTS descuento_pct")
    op.execute("ALTER TABLE ventas DROP COLUMN IF EXISTS descuento_puntos")
