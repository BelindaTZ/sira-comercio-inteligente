"""T046 (Principio X) — un permiso de tabla no puede existir sin el permiso de
módulo (FR-013 Acceptance Scenario 3, Edge Case). Lo garantiza la FK compuesta de
`role_permisos_tabla` → `role_permisos_modulo`, no lógica de aplicación.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.asyncio


async def test_permiso_tabla_sin_permiso_modulo_es_rechazado_por_el_esquema(db_session):
    # Jefe_RRHH no tiene acceso al módulo `Comercial` → insertar un permiso de
    # tabla suyo ahí debe fallar por la FK compuesta.
    role_id = await db_session.scalar(
        text("SELECT role_id FROM roles WHERE nombre = 'Jefe_RRHH'")
    )
    modulo_id = await db_session.scalar(
        text("SELECT modulo_id FROM modulos WHERE nombre = 'Comercial'")
    )
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                "INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select) "
                "VALUES (:r, :m, 'productos', true)"
            ),
            {"r": role_id, "m": modulo_id},
        )
        await db_session.flush()
    await db_session.rollback()
