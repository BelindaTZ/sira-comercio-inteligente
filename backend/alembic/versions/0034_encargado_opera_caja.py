"""El Encargado de Tienda puede abrir y cerrar (cuadrar) una caja, no sólo verla.

Feature 018: la apertura y el cuadre eran acción exclusiva del Cajero (006,
FR-001/FR-002), pero el Encargado necesita poder cubrir una caja o hacer el
cierre del turno cuando el cajero no está. Ya tenía `can_select` sobre
`apertura_caja` y `cierre_caja`; se le añade `can_insert`. Sigue sin poder
editar cierres ya registrados.

Revision ID: 0034
Revises: 0033
Create Date: 2026-09-09

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE role_permisos_tabla
        SET can_insert = true
        WHERE nombre_tabla IN ('apertura_caja', 'cierre_caja')
          AND role_id = (SELECT role_id FROM roles WHERE nombre = 'Encargado_Tienda')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE role_permisos_tabla
        SET can_insert = false
        WHERE nombre_tabla IN ('apertura_caja', 'cierre_caja')
          AND role_id = (SELECT role_id FROM roles WHERE nombre = 'Encargado_Tienda')
        """
    )
