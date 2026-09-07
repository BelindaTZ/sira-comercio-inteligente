"""T019 — contrato POST /api/ventas/{id}/confirmar (FR-002, FR-004, FR-005, FR-036)."""

import pytest
from sqlalchemy import text
from src.integrations.stripe_client import ResultadoIntento
from src.modules.ventas import service as ventas_service

pytestmark = pytest.mark.asyncio


async def _venta_con_lineas(client, escenario_pos, auth, cantidad=2):
    venta = (
        await client.post(
            "/api/ventas",
            json={
                "tienda_id": escenario_pos["tienda_id"],
                "cajero_id": escenario_pos["cajero_id"],
            },
            headers=auth,
        )
    ).json()
    await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas",
        json={"product_id": escenario_pos["product_id"], "cantidad": cantidad},
        headers=auth,
    )
    return venta["venta_id"]


async def test_confirmar_en_efectivo_descuenta_inventario(
    client, escenario_pos, auth_cajero, db_session
):
    venta_id = await _venta_con_lineas(client, escenario_pos, auth_cajero, cantidad=10)

    resp = await client.post(
        f"/api/ventas/{venta_id}/confirmar",
        json={"medio_pago_id": escenario_pos["medio_efectivo"], "tipo_comprobante": "nota_venta"},
        headers=auth_cajero,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["estado"] == "confirmada"
    assert body["total"] == "25.00"  # 10 * 2.50

    disponible = await db_session.scalar(
        text(
            "SELECT cantidad_disponible FROM inventario " "WHERE product_id = :p AND tienda_id = :t"
        ),
        {"p": escenario_pos["product_id"], "t": escenario_pos["tienda_id"]},
    )
    assert disponible == 90  # 100 - 10 (SC-002)


async def test_confirmar_descuenta_primero_el_lote_que_vence_antes(
    client, escenario_pos, auth_cajero, db_session
):
    venta_id = await _venta_con_lineas(client, escenario_pos, auth_cajero, cantidad=10)
    await client.post(
        f"/api/ventas/{venta_id}/confirmar",
        json={"medio_pago_id": escenario_pos["medio_efectivo"]},
        headers=auth_cajero,
    )

    saldo_a = await db_session.scalar(
        text("SELECT cantidad_disponible FROM lotes WHERE lote_id = :l"),
        {"l": escenario_pos["lote_a"]},
    )
    saldo_b = await db_session.scalar(
        text("SELECT cantidad_disponible FROM lotes WHERE lote_id = :l"),
        {"l": escenario_pos["lote_b"]},
    )
    assert saldo_a == 30  # 40 - 10, se consumió el que vence antes (FEFO)
    assert saldo_b == 60  # intacto


async def test_confirmar_con_tarjeta_sin_intento_aprobado_falla(client, escenario_pos, auth_cajero):
    venta_id = await _venta_con_lineas(client, escenario_pos, auth_cajero)
    resp = await client.post(
        f"/api/ventas/{venta_id}/confirmar",
        json={"medio_pago_id": escenario_pos["medio_tarjeta"]},
        headers=auth_cajero,
    )
    assert resp.status_code == 422, resp.text


async def test_confirmar_con_tarjeta_aprobada_ok(client, escenario_pos, auth_cajero, monkeypatch):
    async def _fake(monto, *, escenario):  # noqa: ARG001
        return ResultadoIntento("aprobado", "pi_fake_ok")

    monkeypatch.setattr(ventas_service.stripe_client, "crear_intento_pago", _fake)

    venta_id = await _venta_con_lineas(client, escenario_pos, auth_cajero)
    await client.post(
        f"/api/ventas/{venta_id}/pago-tarjeta",
        json={"monto": "5.00", "escenario": "aprobado"},
        headers=auth_cajero,
    )
    resp = await client.post(
        f"/api/ventas/{venta_id}/confirmar",
        json={"medio_pago_id": escenario_pos["medio_tarjeta"]},
        headers=auth_cajero,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "confirmada"


async def test_factura_exige_identificacion(client, escenario_pos, auth_cajero):
    venta_id = await _venta_con_lineas(client, escenario_pos, auth_cajero)
    resp = await client.post(
        f"/api/ventas/{venta_id}/confirmar",
        json={"medio_pago_id": escenario_pos["medio_efectivo"], "tipo_comprobante": "factura"},
        headers=auth_cajero,
    )
    assert resp.status_code == 422
