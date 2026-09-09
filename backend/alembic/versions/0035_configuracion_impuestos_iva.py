"""Tabla general de configuración de impuestos (IVA 15% Ecuador) no editable en UI.

Almacena la tarifa general vigente de IVA (15% en Ecuador) y el código de
porcentaje del SRI correspondiente. Los roles operativos y comerciales tienen
permiso exclusivo de lectura (can_select); no es editable desde la UI (can_insert,
can_update y can_delete en false) por tratarse de un parámetro fiscal sensible
que solo debe ajustarse directamente a nivel de base de datos.

Revision ID: 0035
Revises: 0034
Create Date: 2026-09-09

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS configuracion_impuestos (
            clave VARCHAR(60) PRIMARY KEY,
            valor DECIMAL(10,4) NOT NULL,
            descripcion VARCHAR(250)
        )
        """
    )
    op.execute(
        """
        INSERT INTO configuracion_impuestos (clave, valor, descripcion) VALUES
            ('iva_porcentaje_vigente', 15.0000, 'Tarifa general vigente del IVA en Ecuador (15%). No editable en la UI; configurable únicamente en base de datos.'),
            ('iva_codigo_sri', 4.0000, 'Código de porcentaje SRI para tarifa de IVA vigente (código 4 = 15% según Ficha Técnica v2.26 del SRI).')
        ON CONFLICT (clave) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
        SELECT r.role_id, m.modulo_id, 'configuracion_impuestos', true, false, false, false
        FROM roles r
        JOIN modulos m ON m.nombre IN ('Ventas', 'Comercial')
        JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
        WHERE r.nombre IN ('Cajero', 'Encargado_Tienda', 'Jefe_Comercial', 'Jefe_Operaciones', 'Jefe_Finanzas', 'Jefe_TI', 'Auditor_Interno')
        ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM role_permisos_tabla WHERE nombre_tabla = 'configuracion_impuestos'")
    op.execute("DROP TABLE IF EXISTS configuracion_impuestos")
