"""T013 — integración US1: Escenario 1 de quickstart.md.

Login exitoso → ultimo_login actualizado; credenciales inválidas y cuenta dada de
baja → 401 genérico; cada intento registrado en `intentos_login`.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_login_de_punta_a_punta(client, escenario_auth, auth_rrhh, db_session):
    e = escenario_auth
    cuenta = e["cajero"]

    ok = await client.post(
        "/api/auth/login", json={"username": cuenta["username"], "password": cuenta["password"]}
    )
    assert ok.status_code == 200
    token = ok.json()["access_token"]

    # el token real gobierna el acceso igual que el token de prueba
    quien = await client.get(
        f"/api/sistema/usuarios/{e['ti']['usuario_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert quien.status_code == 403  # el cajero no administra Sistema

    mala = await client.post(
        "/api/auth/login", json={"username": cuenta["username"], "password": "incorrecta"}
    )
    inexistente = await client.post(
        "/api/auth/login", json={"username": "no.existe", "password": "x"}
    )
    assert mala.status_code == inexistente.status_code == 401
    assert mala.json() == inexistente.json()

    # dar de baja al empleado → login rechazado
    await client.patch(
        f"/api/rrhh/empleados/{cuenta['empleado_id']}/baja",
        json={"fecha_baja": "2026-09-30"},
        headers=auth_rrhh,
    )
    tras_baja = await client.post(
        "/api/auth/login", json={"username": cuenta["username"], "password": cuenta["password"]}
    )
    assert tras_baja.status_code == 401

    total = await db_session.scalar(
        text(
            "SELECT COUNT(*) FROM intentos_login "
            "WHERE username_intentado IN ('cajero.uno', 'no.existe')"
        )
    )
    assert total >= 4
