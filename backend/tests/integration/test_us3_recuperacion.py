"""T025 — integración US3: Escenario 3 de quickstart.md.

Solicitar recuperación → confirmar con el token → login con la nueva contraseña →
reintentar el mismo token (rechazado) → cambio de contraseña propia autenticado.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_recuperacion_de_un_solo_uso_y_cambio_propio(client, escenario_auth, db_session):
    e = escenario_auth
    cuenta = e["cajero"]

    await client.post("/api/auth/recuperar-password", json={"email": cuenta["email"]})
    token = await db_session.scalar(
        text(
            "SELECT token FROM recuperacion_password WHERE usuario_id = :u "
            "ORDER BY token_id DESC LIMIT 1"
        ),
        {"u": cuenta["usuario_id"]},
    )
    assert token

    confirmar = await client.post(
        "/api/auth/recuperar-password/confirmar",
        json={"token": token, "password_nueva": "Recuperada-2026"},
    )
    assert confirmar.status_code == 200

    login = await client.post(
        "/api/auth/login", json={"username": cuenta["username"], "password": "Recuperada-2026"}
    )
    assert login.status_code == 200
    nuevo_token = login.json()["access_token"]

    reuso = await client.post(
        "/api/auth/recuperar-password/confirmar",
        json={"token": token, "password_nueva": "Otra-Vez-2026"},
    )
    assert reuso.status_code == 410

    cambio = await client.patch(
        "/api/auth/mi-password",
        json={"password_actual": "Recuperada-2026", "password_nueva": "Final-2026-zzz"},
        headers={"Authorization": f"Bearer {nuevo_token}"},
    )
    assert cambio.status_code == 200

    viejo = await client.post(
        "/api/auth/login", json={"username": cuenta["username"], "password": "Recuperada-2026"}
    )
    assert viejo.status_code == 401
    final = await client.post(
        "/api/auth/login", json={"username": cuenta["username"], "password": "Final-2026-zzz"}
    )
    assert final.status_code == 200
