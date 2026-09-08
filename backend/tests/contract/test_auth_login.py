"""T012 — contrato de `POST /api/auth/login` (`contracts/auth-administracion-sistema.md`).

Rechazo sin distinguir causa (FR-002/FR-003) y registro de cada intento en
`intentos_login`.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_login_exitoso_devuelve_token_y_actualiza_ultimo_login(
    client, escenario_auth, db_session
):
    e = escenario_auth
    resp = await client.post(
        "/api/auth/login",
        json={"username": e["cajero"]["username"], "password": e["cajero"]["password"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["usuario_id"] == e["cajero"]["usuario_id"]
    assert body["access_token"] and body["expira_en"] > 0

    ultimo = await db_session.scalar(
        text("SELECT ultimo_login FROM usuarios WHERE usuario_id = :u"),
        {"u": e["cajero"]["usuario_id"]},
    )
    assert ultimo is not None


async def test_password_incorrecta_y_usuario_inexistente_dan_el_mismo_401(client, escenario_auth):
    e = escenario_auth
    r1 = await client.post(
        "/api/auth/login", json={"username": e["cajero"]["username"], "password": "no-es"}
    )
    r2 = await client.post(
        "/api/auth/login", json={"username": "nadie.existe", "password": "cualquiera"}
    )
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()  # mensaje genérico idéntico


async def test_cuenta_inactiva_da_el_mismo_401(client, escenario_auth, db_session):
    e = escenario_auth
    await db_session.execute(
        text("UPDATE usuarios SET activo = false WHERE usuario_id = :u"),
        {"u": e["cajero"]["usuario_id"]},
    )
    await db_session.flush()
    resp = await client.post(
        "/api/auth/login",
        json={"username": e["cajero"]["username"], "password": e["cajero"]["password"]},
    )
    assert resp.status_code == 401


async def test_cada_intento_queda_registrado(client, escenario_auth, db_session):
    e = escenario_auth
    await client.post(
        "/api/auth/login",
        json={"username": e["cajero"]["username"], "password": e["cajero"]["password"]},
    )
    await client.post(
        "/api/auth/login", json={"username": e["cajero"]["username"], "password": "mala"}
    )
    await client.post("/api/auth/login", json={"username": "fantasma", "password": "x"})

    exitosos = await db_session.scalar(
        text(
            "SELECT COUNT(*) FROM intentos_login WHERE usuario_id = :u AND exitoso"
        ),
        {"u": e["cajero"]["usuario_id"]},
    )
    fallidos_conocidos = await db_session.scalar(
        text("SELECT COUNT(*) FROM intentos_login WHERE usuario_id = :u AND NOT exitoso"),
        {"u": e["cajero"]["usuario_id"]},
    )
    fallidos_anonimos = await db_session.scalar(
        text(
            "SELECT COUNT(*) FROM intentos_login "
            "WHERE usuario_id IS NULL AND username_intentado = 'fantasma'"
        )
    )
    assert exitosos == 1 and fallidos_conocidos == 1 and fallidos_anonimos == 1


async def test_endpoint_protegido_sin_token_da_401(client):
    resp = await client.get("/api/ventas", params={"tienda_id": 1})
    assert resp.status_code == 401
