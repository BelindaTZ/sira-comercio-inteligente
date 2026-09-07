"""T051 — contrato GET /api/clientes?search= localiza por documento_identidad
igual que por nombre/email (Ronda 5)."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_search_por_cedula(client, escenario_pos, auth_cajero):
    await client.post(
        "/api/clientes",
        json={
            "nombre": "Carlos Ruiz",
            "email": "carlos@example.com",
            "documento_identidad": "1717171717",
            "consentimiento_datos": True,
        },
        headers=auth_cajero,
    )

    por_cedula = await client.get(
        "/api/clientes", params={"search": "1717171717"}, headers=auth_cajero
    )
    por_nombre = await client.get("/api/clientes", params={"search": "Carlos"}, headers=auth_cajero)
    por_email = await client.get(
        "/api/clientes", params={"search": "carlos@example"}, headers=auth_cajero
    )

    for resp in (por_cedula, por_nombre, por_email):
        assert resp.status_code == 200, resp.text
        ids = {c["household_id"] for c in resp.json()["items"]}
        assert any(c["documento_identidad"] == "1717171717" for c in resp.json()["items"]), ids


async def test_search_sin_coincidencia_devuelve_vacio(client, escenario_pos, auth_cajero):
    resp = await client.get(
        "/api/clientes", params={"search": "zzz-no-existe-zzz"}, headers=auth_cajero
    )
    assert resp.status_code == 200
    assert resp.json()["items"] == []
