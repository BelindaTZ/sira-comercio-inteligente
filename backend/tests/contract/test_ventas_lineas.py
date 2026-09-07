"""T016 — contrato POST /api/ventas y POST /api/ventas/{id}/lineas (FR-001, FR-006)."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_iniciar_venta_devuelve_201_y_estado_en_curso(client, escenario_pos, auth_cajero):
    resp = await client.post(
        "/api/ventas",
        json={"tienda_id": escenario_pos["tienda_id"], "cajero_id": escenario_pos["cajero_id"]},
        headers=auth_cajero,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["estado"] == "en_curso"
    assert body["venta_id"] >= 100_000_000_000  # generador del POS, no basket_id sembrado
    assert body["total"] == "0.00"


async def test_agregar_linea_por_barcode_recalcula_total(client, escenario_pos, auth_cajero):
    venta = (
        await client.post(
            "/api/ventas",
            json={
                "tienda_id": escenario_pos["tienda_id"],
                "cajero_id": escenario_pos["cajero_id"],
            },
            headers=auth_cajero,
        )
    ).json()

    resp = await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas",
        json={"codigo_barras": escenario_pos["codigo_barras"], "cantidad": 3},
        headers=auth_cajero,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["lineas"]) == 1
    assert body["lineas"][0]["cantidad"] == 3
    assert body["total"] == "7.50"  # 3 * 2.50


async def test_agregar_linea_que_excede_stock_devuelve_409(client, escenario_pos, auth_cajero):
    venta = (
        await client.post(
            "/api/ventas",
            json={
                "tienda_id": escenario_pos["tienda_id"],
                "cajero_id": escenario_pos["cajero_id"],
            },
            headers=auth_cajero,
        )
    ).json()

    resp = await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas",
        json={"product_id": escenario_pos["product_id"], "cantidad": 999},
        headers=auth_cajero,
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "conflict"


async def test_endpoint_exige_autenticacion(client, escenario_pos):
    resp = await client.post(
        "/api/ventas",
        json={"tienda_id": escenario_pos["tienda_id"], "cajero_id": escenario_pos["cajero_id"]},
    )
    assert resp.status_code == 401
