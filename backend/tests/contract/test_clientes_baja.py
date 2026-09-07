"""T009 — contrato DELETE /api/clientes/{id} (FR-003).

Anonimización real de nombre/email/teléfono/fecha_nacimiento; `household_id`
intacto. Sólo Encargado_Tienda / Jefe_Marketing.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _alta(client, auth, **kw):
    base = {
        "nombre": "Para Baja",
        "email": "baja@example.com",
        "telefono": "0988888888",
        "fecha_nacimiento": "1990-05-05",
        "consentimiento_datos": True,
    }
    base.update(kw)
    return (await client.post("/api/clientes", json=base, headers=auth)).json()


async def test_baja_anonimiza_y_conserva_household_id(
    client, escenario_pos, auth_cajero, auth_encargado, db_session
):
    c = await _alta(client, auth_cajero)
    hid = c["household_id"]

    resp = await client.delete(f"/api/clientes/{hid}", headers=auth_encargado)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["household_id"] == hid
    assert body["activo"] is False
    assert body["nombre"] == "CLIENTE ANONIMIZADO"
    assert body["email"] == f"anon-{hid}@anonimizado.local"
    assert body["telefono"] is None
    assert body["fecha_nacimiento"] is None

    # el registro sigue existiendo
    existe = await db_session.scalar(
        text("SELECT COUNT(*) FROM clientes WHERE household_id = :h"), {"h": hid}
    )
    assert existe == 1


async def test_cajero_no_puede_dar_de_baja(client, escenario_pos, auth_cajero):
    c = await _alta(client, auth_cajero, email="nobaja@example.com")
    resp = await client.delete(f"/api/clientes/{c['household_id']}", headers=auth_cajero)
    assert resp.status_code == 403, resp.text


async def test_baja_de_cliente_inexistente_da_404(client, escenario_pos, auth_encargado):
    resp = await client.delete("/api/clientes/99999999", headers=auth_encargado)
    assert resp.status_code == 404
