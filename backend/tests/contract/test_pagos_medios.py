"""Contrato de medios de pago (`contracts/pagos-seguridad.md`, FR-005 a FR-007)."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_alta_baja_y_disponibles(client, escenario_pagos, auth_caja_ti, auth_cajero):
    alta = await client.post(
        "/api/ventas/medios-pago", json={"nombre": "Billetera XYZ"}, headers=auth_caja_ti
    )
    assert alta.status_code == 201, alta.text
    body = alta.json()
    assert body["aprobado"] is True
    assert body["aprobado_por"] is not None and body["fecha_aprobacion"] is not None
    medio_id = body["medio_pago_id"]

    disponibles = await client.get("/api/ventas/medios-pago/disponibles", headers=auth_cajero)
    assert disponibles.status_code == 200
    assert any(m["nombre"] == "Billetera XYZ" for m in disponibles.json())

    baja = await client.patch(
        f"/api/ventas/medios-pago/{medio_id}/baja", headers=auth_caja_ti
    )
    assert baja.status_code == 200 and baja.json()["aprobado"] is False
    assert baja.json()["fecha_baja"] is not None

    # 409 al re-dar de baja
    otra = await client.patch(f"/api/ventas/medios-pago/{medio_id}/baja", headers=auth_caja_ti)
    assert otra.status_code == 409, otra.text

    disponibles2 = await client.get("/api/ventas/medios-pago/disponibles", headers=auth_cajero)
    assert all(m["nombre"] != "Billetera XYZ" for m in disponibles2.json())


async def test_alta_duplicada_da_409(client, escenario_pagos, auth_caja_ti, db_session):
    await db_session.execute(text("INSERT INTO medios_pago (nombre) VALUES ('Cheque')"))
    await db_session.flush()
    resp = await client.post(
        "/api/ventas/medios-pago", json={"nombre": "Cheque"}, headers=auth_caja_ti
    )
    assert resp.status_code == 409, resp.text


async def test_cajero_no_administra_medios_pago(client, escenario_pagos, auth_cajero):
    resp = await client.get("/api/ventas/medios-pago", headers=auth_cajero)
    assert resp.status_code == 403, resp.text
    resp2 = await client.post(
        "/api/ventas/medios-pago", json={"nombre": "X"}, headers=auth_cajero
    )
    assert resp2.status_code == 403, resp2.text
