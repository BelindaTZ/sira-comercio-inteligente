"""T008 — contrato PATCH /api/clientes/{id} (FR-002).

No altera CLV/churn previos; revocar `consentimiento_datos` no anonimiza nada y
actualiza `fecha_consentimiento_datos`.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _alta(client, auth, **kw):
    base = {"nombre": "Base", "email": "base@example.com", "consentimiento_datos": True}
    base.update(kw)
    return (await client.post("/api/clientes", json=base, headers=auth)).json()


async def test_patch_datos_de_contacto(client, escenario_pos, auth_cajero):
    c = await _alta(client, auth_cajero, email="patch1@example.com")
    resp = await client.patch(
        f"/api/clientes/{c['household_id']}",
        json={"telefono": "0999999999", "nombre": "Nombre Nuevo"},
        headers=auth_cajero,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["telefono"] == "0999999999"
    assert resp.json()["nombre"] == "Nombre Nuevo"


async def test_revocar_consentimiento_no_anonimiza(client, escenario_pos, auth_cajero, db_session):
    c = await _alta(client, auth_cajero, email="revoca@example.com")
    resp = await client.patch(
        f"/api/clientes/{c['household_id']}",
        json={"consentimiento_datos": False},
        headers=auth_cajero,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["consentimiento_datos"] is False
    assert body["nombre"] == "Base"  # NO anonimizado
    assert body["email"] == "revoca@example.com"
    assert body["activo"] is True

    # vuelve a otorgarlo → reincorpora hacia adelante
    r2 = await client.patch(
        f"/api/clientes/{c['household_id']}",
        json={"consentimiento_datos": True},
        headers=auth_cajero,
    )
    assert r2.json()["consentimiento_datos"] is True


async def test_patch_no_altera_clv_previo(client, escenario_pos, auth_cajero, db_session):
    c = await _alta(client, auth_cajero, email="clvprev@example.com")
    hid = c["household_id"]
    await db_session.execute(
        text(
            "INSERT INTO cliente_clv (household_id, clv_score, fecha_calculo) "
            "VALUES (:h, 123.45, CURRENT_DATE)"
        ),
        {"h": hid},
    )
    await db_session.flush()

    await client.patch(f"/api/clientes/{hid}", json={"nombre": "Cambiado"}, headers=auth_cajero)
    clv = await db_session.scalar(
        text("SELECT clv_score FROM cliente_clv WHERE household_id = :h"), {"h": hid}
    )
    assert str(clv) == "123.45"  # intacto


async def test_patch_agrega_datos_demograficos(client, escenario_pos, auth_cajero):
    """FR-004: los datos demográficos son opcionales — no se dan en el alta y se
    pueden agregar después vía PATCH."""
    c = await _alta(client, auth_cajero, email="demo-patch@example.com")
    assert c["datos_demograficos"] is None  # el alta no los exigió

    resp = await client.patch(
        f"/api/clientes/{c['household_id']}",
        json={"datos_demograficos": {"age": "25-34", "marital_status": "Single"}},
        headers=auth_cajero,
    )
    assert resp.status_code == 200, resp.text
    demo = resp.json()["datos_demograficos"]
    assert demo["age"] == "25-34"
    assert demo["marital_status"] == "Single"


async def test_patch_email_a_uno_existente_da_409(client, escenario_pos, auth_cajero):
    await _alta(client, auth_cajero, email="ocupado@example.com")
    c = await _alta(client, auth_cajero, email="libre@example.com")
    resp = await client.patch(
        f"/api/clientes/{c['household_id']}",
        json={"email": "ocupado@example.com"},
        headers=auth_cajero,
    )
    assert resp.status_code == 409, resp.text
