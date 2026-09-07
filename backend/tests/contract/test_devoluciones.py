"""T069 — contrato POST /api/ventas/{id}/devoluciones (FR-025, FR-026)."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _venta_confirmada(client, e, auth, cantidad=5):
    venta = (
        await client.post(
            "/api/ventas",
            json={"tienda_id": e["tienda_id"], "cajero_id": e["cajero_id"]},
            headers=auth,
        )
    ).json()
    await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas",
        json={"product_id": e["product_id"], "cantidad": cantidad},
        headers=auth,
    )
    await client.post(
        f"/api/ventas/{venta['venta_id']}/confirmar",
        json={"medio_pago_id": e["medio_efectivo"]},
        headers=auth,
    )
    return venta["venta_id"]


async def test_devolucion_por_motivo_valido_reintegra_stock(
    client, escenario_pos, auth_cajero, db_session
):
    e = escenario_pos
    venta_id = await _venta_confirmada(client, e, auth_cajero, cantidad=5)  # inventario 100 -> 95

    resp = await client.post(
        f"/api/ventas/{venta_id}/devoluciones",
        json={
            "product_id": e["product_id"],
            "cantidad": 2,
            "motivo": "El cliente cambió de opinión",
        },
        headers=auth_cajero,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["reintegra_inventario"] is True

    disponible = await db_session.scalar(
        text("SELECT cantidad_disponible FROM inventario WHERE product_id = :p AND tienda_id = :t"),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    assert disponible == 97  # 95 + 2


async def test_devolucion_por_producto_danado_no_reintegra(
    client, escenario_pos, auth_cajero, db_session
):
    e = escenario_pos
    venta_id = await _venta_confirmada(client, e, auth_cajero, cantidad=5)

    resp = await client.post(
        f"/api/ventas/{venta_id}/devoluciones",
        json={
            "product_id": e["product_id"],
            "cantidad": 1,
            "motivo": "Producto dañado por el cliente",
        },
        headers=auth_cajero,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["reintegra_inventario"] is False

    disponible = await db_session.scalar(
        text("SELECT cantidad_disponible FROM inventario WHERE product_id = :p AND tienda_id = :t"),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    assert disponible == 95  # sin cambio


async def test_devolucion_que_excede_lo_vendido_da_409(client, escenario_pos, auth_cajero):
    e = escenario_pos
    venta_id = await _venta_confirmada(client, e, auth_cajero, cantidad=3)
    resp = await client.post(
        f"/api/ventas/{venta_id}/devoluciones",
        json={"product_id": e["product_id"], "cantidad": 10, "motivo": "cambio"},
        headers=auth_cajero,
    )
    assert resp.status_code == 409, resp.text


async def test_devolucion_de_producto_no_vendido_en_la_venta(client, escenario_pos, auth_cajero):
    e = escenario_pos
    venta_id = await _venta_confirmada(client, e, auth_cajero, cantidad=2)
    resp = await client.post(
        f"/api/ventas/{venta_id}/devoluciones",
        json={"product_id": 999999999, "cantidad": 1, "motivo": "cambio"},
        headers=auth_cajero,
    )
    assert resp.status_code == 422, resp.text
