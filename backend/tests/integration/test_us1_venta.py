"""T022 — integración US1: Escenarios 1 y 2 de quickstart.md.

1. Venta completa con tarjeta aprobada → inventario descontado, comprobante accesible.
2. Tarjeta rechazada y reintento con efectivo → venta confirmada sin perder líneas.
"""

import pytest
from sqlalchemy import text
from src.integrations.stripe_client import ResultadoIntento
from src.modules.ventas import service as ventas_service

pytestmark = pytest.mark.asyncio


async def _abrir_venta(client, escenario_pos, auth):
    return (
        await client.post(
            "/api/ventas",
            json={
                "tienda_id": escenario_pos["tienda_id"],
                "cajero_id": escenario_pos["cajero_id"],
            },
            headers=auth,
        )
    ).json()["venta_id"]


async def test_escenario_1_venta_con_tarjeta_aprobada(
    client, escenario_pos, auth_cajero, monkeypatch, db_session
):
    async def _aprobado(monto, *, escenario):  # noqa: ARG001
        return ResultadoIntento("aprobado", "pi_test_ok")

    monkeypatch.setattr(ventas_service.stripe_client, "crear_intento_pago", _aprobado)

    venta_id = await _abrir_venta(client, escenario_pos, auth_cajero)
    for _ in range(3):
        await client.post(
            f"/api/ventas/{venta_id}/lineas",
            json={"codigo_barras": escenario_pos["codigo_barras"], "cantidad": 1},
            headers=auth_cajero,
        )

    pago = await client.post(
        f"/api/ventas/{venta_id}/pago-tarjeta",
        json={"monto": "7.50", "escenario": "aprobado"},
        headers=auth_cajero,
    )
    assert pago.json()["resultado"] == "aprobado"

    conf = await client.post(
        f"/api/ventas/{venta_id}/confirmar",
        json={"medio_pago_id": escenario_pos["medio_tarjeta"], "tipo_comprobante": "nota_venta"},
        headers=auth_cajero,
    )
    assert conf.status_code == 200, conf.text
    assert conf.json()["estado"] == "confirmada"

    # SC-002: inventario reflejado
    disponible = await db_session.scalar(
        text("SELECT cantidad_disponible FROM inventario WHERE product_id = :p AND tienda_id = :t"),
        {"p": escenario_pos["product_id"], "t": escenario_pos["tienda_id"]},
    )
    assert disponible == 97  # 100 - 3

    # trazabilidad venta -> línea -> lote (FR-026)
    movimientos = await db_session.scalar(
        text(
            "SELECT COUNT(*) FROM movimientos_inventario "
            "WHERE referencia_tabla = 'venta_detalle' AND tipo = 'salida' AND lote_id IS NOT NULL "
            "AND referencia_id IN (SELECT venta_detalle_id FROM venta_detalle WHERE venta_id = :v)"
        ),
        {"v": venta_id},
    )
    assert movimientos == 3


async def test_escenario_2_rechazo_y_reintento_con_efectivo(
    client, escenario_pos, auth_cajero, monkeypatch, db_session
):
    async def _rechazado(monto, *, escenario):  # noqa: ARG001
        return ResultadoIntento("rechazado", "pi_test_declined", "insufficient_funds")

    monkeypatch.setattr(ventas_service.stripe_client, "crear_intento_pago", _rechazado)

    venta_id = await _abrir_venta(client, escenario_pos, auth_cajero)
    for _ in range(2):
        await client.post(
            f"/api/ventas/{venta_id}/lineas",
            json={"product_id": escenario_pos["product_id"], "cantidad": 1},
            headers=auth_cajero,
        )

    rechazo = await client.post(
        f"/api/ventas/{venta_id}/pago-tarjeta",
        json={"monto": "5.00", "escenario": "rechazado"},
        headers=auth_cajero,
    )
    assert rechazo.json()["resultado"] == "rechazado"

    # FR-031: se reintenta con efectivo sin haber perdido las líneas
    conf = await client.post(
        f"/api/ventas/{venta_id}/confirmar",
        json={"medio_pago_id": escenario_pos["medio_efectivo"]},
        headers=auth_cajero,
    )
    assert conf.status_code == 200, conf.text
    body = conf.json()
    assert body["estado"] == "confirmada"
    assert len(body["lineas"]) == 2
    assert body["total"] == "5.00"

    intentos = await db_session.scalar(
        text("SELECT COUNT(*) FROM intentos_pago_tarjeta WHERE venta_id = :v"),
        {"v": venta_id},
    )
    assert intentos == 1  # el rechazo quedó registrado
