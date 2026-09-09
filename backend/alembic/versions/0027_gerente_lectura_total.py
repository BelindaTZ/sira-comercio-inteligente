"""Gerente_General: lectura (select) sobre todas las tablas de sus módulos.

`Gerente_General` tenía los 9 módulos con `puede_ver = true` pero sólo 8 filas en
`role_permisos_tabla` (dashboards de la feature 009). Resultado: la nav le mostraba
todas las pantallas (bypass `esGerente` en el front) pero el backend le devolvía
403 en cada data-grid operativo.

El plan (`.specify/memory/...` y Fase 0 de 013) define al Gerente como rol
ejecutivo de **lectura total**. Esta migración cierra la brecha: `can_select` en
toda tabla que cualquier otro rol pueda leer, dentro de un módulo que el Gerente
ya ve. NO se le da insert/update/delete (todos sus módulos son `puede_editar = false`).

Revision ID: 0027
Revises: 0026
Create Date: 2026-09-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE = """
INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                 can_select, can_insert, can_update, can_delete)
SELECT DISTINCT g.role_id, t.modulo_id, t.nombre_tabla, true, false, false, false
FROM (SELECT role_id FROM roles WHERE nombre = 'Gerente_General') g
JOIN role_permisos_modulo rpm ON rpm.role_id = g.role_id AND rpm.puede_ver
JOIN role_permisos_tabla t ON t.modulo_id = rpm.modulo_id
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING
"""

DOWNGRADE = """
DELETE FROM role_permisos_tabla
WHERE role_id = (SELECT role_id FROM roles WHERE nombre = 'Gerente_General')
  AND NOT (can_insert OR can_update OR can_delete)
  AND nombre_tabla NOT IN ('dashboard_kpi', 'registro_publicacion_dashboard')
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
