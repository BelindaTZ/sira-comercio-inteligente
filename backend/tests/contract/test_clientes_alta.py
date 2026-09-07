"""T007 — contrato POST /api/clientes (FR-001, Ronda 5).

Rechaza email duplicado; acepta `consentimiento_datos: false` sin bloquear el
alta; acepta `documento_identidad` opcional y da 409 si ya existe.
"""

import pytest

pytestmark = pytest.mark.asyncio


def _cli(**kw):
    base = {"nombre": "Ana Pérez", "email": "ana@example.com", "consentimiento_datos": True}
    base.update(kw)
    return base


async def test_alta_basica(client, escenario_pos, auth_cajero):
    resp = await client.post("/api/clientes", json=_cli(), headers=auth_cajero)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["household_id"] >= 900_000  # generador de altas nuevas
    assert body["consentimiento_datos"] is True
    assert body["activo"] is True


async def test_alta_con_consentimiento_rechazado_no_bloquea(client, escenario_pos, auth_cajero):
    resp = await client.post(
        "/api/clientes",
        json=_cli(email="sinconsent@example.com", consentimiento_datos=False),
        headers=auth_cajero,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["consentimiento_datos"] is False


async def test_email_duplicado_da_409(client, escenario_pos, auth_cajero):
    await client.post("/api/clientes", json=_cli(email="dup@example.com"), headers=auth_cajero)
    resp = await client.post(
        "/api/clientes", json=_cli(nombre="Otro", email="dup@example.com"), headers=auth_cajero
    )
    assert resp.status_code == 409, resp.text


async def test_documento_duplicado_da_409(client, escenario_pos, auth_cajero):
    await client.post(
        "/api/clientes",
        json=_cli(email="d1@example.com", documento_identidad="0102030405"),
        headers=auth_cajero,
    )
    resp = await client.post(
        "/api/clientes",
        json=_cli(email="d2@example.com", documento_identidad="0102030405"),
        headers=auth_cajero,
    )
    assert resp.status_code == 409, resp.text


async def test_alta_con_datos_demograficos(client, escenario_pos, auth_cajero):
    resp = await client.post(
        "/api/clientes",
        json=_cli(
            email="demo@example.com", datos_demograficos={"age": "35-44", "income": "50-74K"}
        ),
        headers=auth_cajero,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["datos_demograficos"]["age"] == "35-44"


async def test_alta_exige_autenticacion(client, escenario_pos):
    resp = await client.post("/api/clientes", json=_cli(email="x@example.com"))
    assert resp.status_code == 401
