"""PIN de autorización por empleado (releva de teclear un id a mano en el POS).

Feature 018: los procesos del POS que exigen la autorización de un supervisor
distinto del cajero (remoción de línea FR-027, descuento manual FR-009) se
autorizan con el PIN del Encargado físicamente presente — nunca con un id que el
cajero teclea. Cada empleado con rol autorizador (`Encargado_Tienda` o un Jefe de
la lista de `contracts/pricing.md`) recibe un PIN de 4 dígitos, visible sólo para
su dueño en "Mi PIN de autorización".

Revision ID: 0031
Revises: 0030
Create Date: 2026-09-09

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROLES_AUTORIZADORES = (
    "Encargado_Tienda",
    "Jefe_Comercial",
    "Jefe_Operaciones",
    "Jefe_Finanzas",
    "Gerente_General",
)


def upgrade() -> None:
    op.execute("ALTER TABLE empleados ADD COLUMN IF NOT EXISTS pin_autorizacion VARCHAR(6)")
    roles = ",".join(f"'{r}'" for r in _ROLES_AUTORIZADORES)
    op.execute(
        f"""
        UPDATE empleados e
        SET pin_autorizacion = lpad((floor(random() * 10000))::int::text, 4, '0')
        FROM usuarios u
        JOIN roles r ON r.role_id = u.role_id
        WHERE u.empleado_id = e.empleado_id
          AND r.nombre IN ({roles})
          AND e.pin_autorizacion IS NULL
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE empleados DROP COLUMN IF EXISTS pin_autorizacion")
