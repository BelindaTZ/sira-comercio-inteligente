"""T038 — integración US5: Escenario 5 de quickstart.md.

Baja de empleado → cuenta inhabilitada por el trigger → login rechazado →
reactivar al empleado no reactiva la cuenta → reporte mensual de auditoría
agrupado por usuario.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_baja_inhabilitacion_automatica_y_reporte(
    client, escenario_auth, auth_rrhh, auth_admin_ti, db_session
):
    e = escenario_auth
    cuenta = e["cajero"]
    ahora = datetime.now(UTC)

    # genera actividad de login del periodo
    await client.post(
        "/api/auth/login", json={"username": cuenta["username"], "password": cuenta["password"]}
    )
    await client.post(
        "/api/auth/login", json={"username": cuenta["username"], "password": "mala"}
    )

    baja = await client.patch(
        f"/api/rrhh/empleados/{cuenta['empleado_id']}/baja",
        json={"fecha_baja": ahora.date().isoformat()},
        headers=auth_rrhh,
    )
    assert baja.status_code == 200

    estado = await client.get(
        f"/api/sistema/usuarios/{cuenta['usuario_id']}", headers=auth_admin_ti
    )
    assert estado.json()["activo"] is False

    rechazado = await client.post(
        "/api/auth/login", json={"username": cuenta["username"], "password": cuenta["password"]}
    )
    assert rechazado.status_code == 401

    # reactivar al empleado NO reactiva la cuenta
    await db_session.execute(
        text("UPDATE empleados SET activo = true, fecha_baja = NULL WHERE empleado_id = :e"),
        {"e": cuenta["empleado_id"]},
    )
    await db_session.flush()
    estado2 = await client.get(
        f"/api/sistema/usuarios/{cuenta['usuario_id']}", headers=auth_admin_ti
    )
    assert estado2.json()["activo"] is False

    reporte = await client.get(
        "/api/sistema/auditoria/reporte-mensual",
        params={"mes": ahora.month, "anio": ahora.year},
        headers=auth_admin_ti,
    )
    assert reporte.status_code == 200, reporte.text
    fila = next(
        (r for r in reporte.json() if r["usuario_id"] == cuenta["usuario_id"]), None
    )
    assert fila is not None
    assert fila["logins_exitosos"] >= 1 and fila["intentos_fallidos"] >= 1
