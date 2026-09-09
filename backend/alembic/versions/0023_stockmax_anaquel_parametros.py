"""Parámetros ricos de Stock Máximo y Verificación de Anaquel (001 — feature 013).

Referencias nuevas de docs/diseno-ui:
- "Configurar Stock Máximo por Categoría" pide, además del tope: capacidad física
  de góndola, punto de reorden (mínimo), días de cobertura objetivo y política
  de sobre-stock.
- "Verificar y Auditar Anaquel en Góndola" pide, además de si el producto está
  disponible: facing asignado vs. real, sincronización ESL, cumplimiento FIFO y
  observaciones del operador.

Todas las columnas son aditivas y opcionales (no rompen inserts existentes).

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    "ALTER TABLE stock_maximo_categoria ADD COLUMN IF NOT EXISTS capacidad_gondola INTEGER",
    "ALTER TABLE stock_maximo_categoria ADD COLUMN IF NOT EXISTS stock_minimo_reorden INTEGER",
    "ALTER TABLE stock_maximo_categoria ADD COLUMN IF NOT EXISTS dias_cobertura INTEGER",
    "ALTER TABLE stock_maximo_categoria ADD COLUMN IF NOT EXISTS politica_sobrestock VARCHAR(20)",
    """DO $$ BEGIN
        ALTER TABLE stock_maximo_categoria ADD CONSTRAINT chk_smc_politica_sobrestock
            CHECK (politica_sobrestock IS NULL OR politica_sobrestock IN ('estricto','autorizado'));
       EXCEPTION WHEN duplicate_object THEN NULL; END $$""",
    "ALTER TABLE verificacion_anaquel ADD COLUMN IF NOT EXISTS facing_asignado INTEGER",
    "ALTER TABLE verificacion_anaquel ADD COLUMN IF NOT EXISTS facing_real INTEGER",
    "ALTER TABLE verificacion_anaquel ADD COLUMN IF NOT EXISTS esl_ok BOOLEAN",
    "ALTER TABLE verificacion_anaquel ADD COLUMN IF NOT EXISTS fifo_ok BOOLEAN",
    "ALTER TABLE verificacion_anaquel ADD COLUMN IF NOT EXISTS observaciones TEXT",
]

DOWNGRADE_STATEMENTS: list[str] = [
    "ALTER TABLE verificacion_anaquel DROP COLUMN IF EXISTS observaciones",
    "ALTER TABLE verificacion_anaquel DROP COLUMN IF EXISTS fifo_ok",
    "ALTER TABLE verificacion_anaquel DROP COLUMN IF EXISTS esl_ok",
    "ALTER TABLE verificacion_anaquel DROP COLUMN IF EXISTS facing_real",
    "ALTER TABLE verificacion_anaquel DROP COLUMN IF EXISTS facing_asignado",
    "ALTER TABLE stock_maximo_categoria DROP CONSTRAINT IF EXISTS chk_smc_politica_sobrestock",
    "ALTER TABLE stock_maximo_categoria DROP COLUMN IF EXISTS politica_sobrestock",
    "ALTER TABLE stock_maximo_categoria DROP COLUMN IF EXISTS dias_cobertura",
    "ALTER TABLE stock_maximo_categoria DROP COLUMN IF EXISTS stock_minimo_reorden",
    "ALTER TABLE stock_maximo_categoria DROP COLUMN IF EXISTS capacidad_gondola",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
