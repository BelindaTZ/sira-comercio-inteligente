"""El Encargado de Tienda puede registrar (no sólo actualizar) un incidente de fraude.

Feature 018: un Encargado que detecta actividad sospechosa en su tienda (faltantes
repetidos de un cajero, anulaciones fuera de patrón) debe poder abrir el caso para
que Finanzas lo investigue. Ya tenía `can_update` (aplicar protocolo / cerrar);
se añade `can_insert` sobre `Finanzas.incidentes_fraude`.

Revision ID: 0030
Revises: 0029
Create Date: 2026-09-09

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE role_permisos_tabla
        SET can_insert = true
        WHERE nombre_tabla = 'incidentes_fraude'
          AND role_id = (SELECT role_id FROM roles WHERE nombre = 'Encargado_Tienda')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE role_permisos_tabla
        SET can_insert = false
        WHERE nombre_tabla = 'incidentes_fraude'
          AND role_id = (SELECT role_id FROM roles WHERE nombre = 'Encargado_Tienda')
        """
    )
