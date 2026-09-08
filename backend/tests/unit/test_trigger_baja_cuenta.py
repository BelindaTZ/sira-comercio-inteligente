"""T037 — el trigger `trg_inhabilitar_cuenta_baja_empleado` (research.md Decisión
4): dar de baja a un empleado inhabilita su cuenta automáticamente, y reactivar
al empleado NO reactiva la cuenta (FR-014, FR-015). Prueba de comportamiento de
esquema (mismo estilo que `test_rbac_ventas_inventario`).
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _empleado_con_cuenta(db_session) -> tuple[int, int]:
    role_id = await db_session.scalar(text("SELECT role_id FROM roles WHERE nombre = 'Cajero'"))
    puesto_id = await db_session.scalar(
        text(
            "INSERT INTO roles_puesto (nombre) VALUES ('P-'||gen_random_uuid()) RETURNING puesto_id"
        )
    )
    empleado_id = await db_session.scalar(
        text(
            "INSERT INTO empleados (puesto_id, nombre, fecha_contratacion) "
            "VALUES (:p, 'Trigger Test', CURRENT_DATE) RETURNING empleado_id"
        ),
        {"p": puesto_id},
    )
    usuario_id = await db_session.scalar(
        text(
            "INSERT INTO usuarios (empleado_id, role_id, username, password_hash) "
            "VALUES (:e, :r, 'trg-'||gen_random_uuid(), 'x') RETURNING usuario_id"
        ),
        {"e": empleado_id, "r": role_id},
    )
    await db_session.flush()
    return empleado_id, usuario_id


async def test_baja_de_empleado_inhabilita_la_cuenta(db_session):
    empleado_id, usuario_id = await _empleado_con_cuenta(db_session)

    await db_session.execute(
        text(
            "UPDATE empleados SET activo = false, fecha_baja = CURRENT_DATE WHERE empleado_id = :e"
        ),
        {"e": empleado_id},
    )
    await db_session.flush()
    assert (
        await db_session.scalar(
            text("SELECT activo FROM usuarios WHERE usuario_id = :u"), {"u": usuario_id}
        )
        is False
    )


async def test_reactivar_empleado_no_reactiva_la_cuenta(db_session):
    empleado_id, usuario_id = await _empleado_con_cuenta(db_session)
    await db_session.execute(
        text("UPDATE empleados SET activo = false WHERE empleado_id = :e"), {"e": empleado_id}
    )
    await db_session.flush()

    await db_session.execute(
        text("UPDATE empleados SET activo = true, fecha_baja = NULL WHERE empleado_id = :e"),
        {"e": empleado_id},
    )
    await db_session.flush()
    # la cuenta sigue inhabilitada hasta que Jefe_TI la reactive explícitamente
    assert (
        await db_session.scalar(
            text("SELECT activo FROM usuarios WHERE usuario_id = :u"), {"u": usuario_id}
        )
        is False
    )
