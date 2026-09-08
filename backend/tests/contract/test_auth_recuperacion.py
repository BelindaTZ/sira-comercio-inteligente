"""Contrato de recuperación y cambio de contraseña (FR-009 a FR-011)."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _token_de(db_session, usuario_id: int) -> str:
    return await db_session.scalar(
        text(
            "SELECT token FROM recuperacion_password WHERE usuario_id = :u "
            "ORDER BY token_id DESC LIMIT 1"
        ),
        {"u": usuario_id},
    )


async def test_recuperacion_responde_igual_exista_o_no_el_email(client, escenario_auth):
    r1 = await client.post(
        "/api/auth/recuperar-password", json={"email": escenario_auth["cajero"]["email"]}
    )
    r2 = await client.post(
        "/api/auth/recuperar-password", json={"email": "nadie@ninguna.parte"}
    )
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()


async def test_confirmar_con_token_valido_y_reuso_rechazado(client, escenario_auth, db_session):
    e = escenario_auth
    await client.post(
        "/api/auth/recuperar-password", json={"email": e["cajero"]["email"]}
    )
    token = await _token_de(db_session, e["cajero"]["usuario_id"])
    assert token

    ok = await client.post(
        "/api/auth/recuperar-password/confirmar",
        json={"token": token, "password_nueva": "Nueva-Clave-2026"},
    )
    assert ok.status_code == 200, ok.text

    login = await client.post(
        "/api/auth/login",
        json={"username": e["cajero"]["username"], "password": "Nueva-Clave-2026"},
    )
    assert login.status_code == 200

    reuso = await client.post(
        "/api/auth/recuperar-password/confirmar",
        json={"token": token, "password_nueva": "Otra-Mas-2026"},
    )
    assert reuso.status_code == 410, reuso.text


async def test_mi_password_self_service(client, escenario_auth):
    e = escenario_auth
    resp = await client.patch(
        "/api/auth/mi-password",
        json={"password_actual": e["cajero"]["password"], "password_nueva": "Cambiada-2026-x"},
        headers={"Authorization": f"Bearer {e['cajero']['token']}"},
    )
    assert resp.status_code == 200, resp.text

    mal = await client.patch(
        "/api/auth/mi-password",
        json={"password_actual": "no-era-esa", "password_nueva": "Cualquiera-2026"},
        headers={"Authorization": f"Bearer {e['cajero']['token']}"},
    )
    assert mal.status_code == 401
