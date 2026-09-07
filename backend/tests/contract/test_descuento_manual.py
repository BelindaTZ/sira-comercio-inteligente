"""T030 — contrato POST /api/ventas/{id}/lineas/{id}/descuento (FR-009, SC-004).

403 si autoriza el mismo cajero; 403 si el rol de quien autoriza no está
habilitado; 200 sin importar el monto si autoriza un Encargado_Tienda distinto.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def _venta_con_linea(client, e, auth):
    venta = (
        await client.post(
            "/api/ventas",
            json={"tienda_id": e["tienda_id"], "cajero_id": e["cajero_id"]},
            headers=auth,
        )
    ).json()
    venta = (
        await client.post(
            f"/api/ventas/{venta['venta_id']}/lineas",
            json={"product_id": e["product_id"], "cantidad": 2},
            headers=auth,
        )
    ).json()
    return venta


async def test_mismo_empleado_aplica_y_autoriza_da_403(client, escenario_pricing, auth_cajero):
    e = escenario_pricing
    venta = await _venta_con_linea(client, e, auth_cajero)
    linea_id = venta["lineas"][0]["venta_detalle_id"]
    resp = await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas/{linea_id}/descuento",
        json={
            "tipo": "monto",
            "valor": "0.50",
            "motivo": "cliente habitual",
            "empleado_aplica_id": e["cajero_id"],
            "empleado_autoriza_id": e["cajero_id"],
        },
        headers=auth_cajero,
    )
    assert resp.status_code == 403, resp.text


async def test_rol_no_habilitado_da_403(client, escenario_pricing, auth_cajero):
    e = escenario_pricing
    venta = await _venta_con_linea(client, e, auth_cajero)
    linea_id = venta["lineas"][0]["venta_detalle_id"]
    resp = await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas/{linea_id}/descuento",
        json={
            "tipo": "monto",
            "valor": "0.50",
            "motivo": "cliente habitual",
            "empleado_aplica_id": e["cajero_id"],
            "empleado_autoriza_id": e["jefe_ti_id"],
        },
        headers=auth_cajero,
    )
    assert resp.status_code == 403, resp.text


async def test_encargado_autoriza_200_sin_importar_el_monto(client, escenario_pricing, auth_cajero):
    e = escenario_pricing
    venta = await _venta_con_linea(client, e, auth_cajero)
    linea_id = venta["lineas"][0]["venta_detalle_id"]
    resp = await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas/{linea_id}/descuento",
        json={
            "tipo": "monto",
            "valor": "0.10",  # monto pequeño: la autorización es obligatoria igual
            "motivo": "cliente habitual",
            "empleado_aplica_id": e["cajero_id"],
            "empleado_autoriza_id": e["encargado_id"],
        },
        headers=auth_cajero,
    )
    assert resp.status_code == 200, resp.text
    linea = resp.json()["lineas"][0]
    assert linea["empleado_autoriza_id"] == e["encargado_id"]
    assert linea["motivo_descuento"] == "cliente habitual"


async def test_motivo_obligatorio(client, escenario_pricing, auth_cajero):
    e = escenario_pricing
    venta = await _venta_con_linea(client, e, auth_cajero)
    linea_id = venta["lineas"][0]["venta_detalle_id"]
    resp = await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas/{linea_id}/descuento",
        json={
            "tipo": "monto",
            "valor": "0.50",
            "motivo": "",
            "empleado_aplica_id": e["cajero_id"],
            "empleado_autoriza_id": e["encargado_id"],
        },
        headers=auth_cajero,
    )
    assert resp.status_code == 422, resp.text
