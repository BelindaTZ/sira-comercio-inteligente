"""Confirmación de la respuesta del proveedor a una orden de compra.

Feature 018 (extensión de 001-US3 pedida por el usuario): sin integración de
correo entrante, un actor humano registra la respuesta del proveedor a un pedido
—automático o especial— con un motivo obligatorio y el canal por el que llegó
(correo / WhatsApp / teléfono / otro). Estados nuevos: `confirmada` (el proveedor
aceptó, la orden puede recibirse) y `rechazada` (el proveedor no la surtirá).

Revision ID: 0029
Revises: 0028
Create Date: 2026-09-09

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE ordenes_compra "
        "ADD COLUMN IF NOT EXISTS proveedor_confirmo BOOLEAN, "
        "ADD COLUMN IF NOT EXISTS respuesta_proveedor TEXT, "
        "ADD COLUMN IF NOT EXISTS canal_respuesta VARCHAR(20), "
        "ADD COLUMN IF NOT EXISTS fecha_respuesta TIMESTAMP, "
        "ADD COLUMN IF NOT EXISTS empleado_respuesta_id INTEGER"
    )
    op.execute("ALTER TABLE ordenes_compra DROP CONSTRAINT IF EXISTS ordenes_compra_estado_check")
    op.execute(
        "ALTER TABLE ordenes_compra ADD CONSTRAINT ordenes_compra_estado_check "
        "CHECK (estado IN ('pendiente','aprobada','confirmada','recibida','rechazada','cancelada'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE ordenes_compra DROP CONSTRAINT IF EXISTS ordenes_compra_estado_check")
    op.execute(
        "ALTER TABLE ordenes_compra ADD CONSTRAINT ordenes_compra_estado_check "
        "CHECK (estado IN ('pendiente','aprobada','recibida','cancelada'))"
    )
    op.execute(
        "ALTER TABLE ordenes_compra "
        "DROP COLUMN IF EXISTS proveedor_confirmo, "
        "DROP COLUMN IF EXISTS respuesta_proveedor, "
        "DROP COLUMN IF EXISTS canal_respuesta, "
        "DROP COLUMN IF EXISTS fecha_respuesta, "
        "DROP COLUMN IF EXISTS empleado_respuesta_id"
    )
