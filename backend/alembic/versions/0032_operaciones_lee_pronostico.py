"""El Jefe de Operaciones puede leer el pronóstico de demanda y su monitoreo.

Feature 018: la pantalla de "Pronóstico de demanda" es del Jefe de TI (entrena y
aprueba modelos — US1/US3), pero el Jefe de Operaciones es el consumidor directo
del pronóstico para la reposición y las compras (US2, FR-007/FR-009/FR-010) y
necesita ver la salud del modelo vigente. Se le concede acceso de SÓLO LECTURA al
módulo TI sobre las cuatro tablas de forecasting (sin poder aprobar ni configurar).

Revision ID: 0032
Revises: 0031
Create Date: 2026-09-09

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLAS = (
    "modelo_demanda",
    "pronostico_demanda",
    "monitoreo_precision_modelo",
    "configuracion_pronostico",
)


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
        SELECT r.role_id, m.modulo_id, true, false
        FROM roles r, modulos m
        WHERE r.nombre = 'Jefe_Operaciones' AND m.nombre = 'TI'
        ON CONFLICT (role_id, modulo_id) DO NOTHING
        """
    )
    op.execute(
        f"""
        INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla,
                                         can_select, can_insert, can_update, can_delete)
        SELECT r.role_id, m.modulo_id, t.tabla, true, false, false, false
        FROM roles r
        JOIN modulos m ON m.nombre = 'TI'
        CROSS JOIN (VALUES {", ".join(f"('{x}')" for x in _TABLAS)}) AS t(tabla)
        WHERE r.nombre = 'Jefe_Operaciones'
        ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING
        """  # noqa: S608 - lista fija, sin entrada externa
    )


def downgrade() -> None:
    op.execute(
        f"""
        DELETE FROM role_permisos_tabla rpt
        USING roles r, modulos m
        WHERE rpt.role_id = r.role_id AND rpt.modulo_id = m.modulo_id
          AND r.nombre = 'Jefe_Operaciones' AND m.nombre = 'TI'
          AND rpt.nombre_tabla IN ({", ".join(f"'{x}'" for x in _TABLAS)})
        """  # noqa: S608
    )
    op.execute(
        """
        DELETE FROM role_permisos_modulo
        WHERE role_id = (SELECT role_id FROM roles WHERE nombre = 'Jefe_Operaciones')
          AND modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'TI')
        """
    )
