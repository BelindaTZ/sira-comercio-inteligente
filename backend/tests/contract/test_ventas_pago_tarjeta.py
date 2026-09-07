"""T018 — contrato POST /api/ventas/{id}/pago-tarjeta: los 3 resultados de FR-030.

`aprobado` / `rechazado` / `error_tecnico` deben ser valores distintos y cada
intento queda registrado en `intentos_pago_tarjeta` (permite reintento, FR-031).
El cajero nunca envía datos de tarjeta (FR-003): el body es sólo `{monto, escenario}`.
"""

import pytest
from sqlalchemy import text
from src.integrations.stripe_client import ResultadoIntento
from src.modules.ventas import service as ventas_service

pytestmark = pytest.mark.asyncio


async def _venta_lista_para_cobro(client, escenario_pos, auth_cajero):
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
    await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas",
        json={"product_id": escenario_pos["product_id"], "cantidad": 2},
        headers=auth_cajero,
    )
    return venta["venta_id"]


@pytest.mark.parametrize(
    ("escenario", "referencia_esperada"),
    [
        ("aprobado", "pi_fake_ok"),
        ("rechazado", "pi_fake_declined"),
        ("error_tecnico", None),
    ],
)
async def test_los_tres_resultados_se_registran(
    client, escenario_pos, auth_cajero, monkeypatch, db_session, escenario, referencia_esperada
):
    async def _fake(monto, *, escenario):  # noqa: ARG001
        return ResultadoIntento(escenario, referencia_esperada)

    monkeypatch.setattr(ventas_service.stripe_client, "crear_intento_pago", _fake)

    venta_id = await _venta_lista_para_cobro(client, escenario_pos, auth_cajero)
    resp = await client.post(
        f"/api/ventas/{venta_id}/pago-tarjeta",
        json={"monto": "5.00", "escenario": escenario},
        headers=auth_cajero,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["resultado"] == escenario
    assert body["referencia_pasarela"] == referencia_esperada

    fila = await db_session.scalar(
        text("SELECT resultado FROM intentos_pago_tarjeta WHERE intento_id = :i"),
        {"i": body["intento_id"]},
    )
    assert fila == escenario


async def test_reintento_tras_rechazo_conserva_las_lineas(
    client, escenario_pos, auth_cajero, monkeypatch
):
    resultados = iter(["rechazado", "aprobado"])

    async def _fake(monto, *, escenario):  # noqa: ARG001
        return ResultadoIntento(next(resultados), "pi_fake")

    monkeypatch.setattr(ventas_service.stripe_client, "crear_intento_pago", _fake)

    venta_id = await _venta_lista_para_cobro(client, escenario_pos, auth_cajero)

    r1 = await client.post(
        f"/api/ventas/{venta_id}/pago-tarjeta",
        json={"monto": "5.00", "escenario": "rechazado"},
        headers=auth_cajero,
    )
    r2 = await client.post(
        f"/api/ventas/{venta_id}/pago-tarjeta",
        json={"monto": "5.00", "escenario": "aprobado"},
        headers=auth_cajero,
    )
    assert r1.json()["resultado"] == "rechazado"
    assert r2.json()["resultado"] == "aprobado"

    venta = (await client.get("/api/ventas", headers=auth_cajero)).json()
    actual = next(v for v in venta["items"] if v["venta_id"] == venta_id)
    assert len(actual["lineas"]) == 1  # FR-031: no se perdieron líneas
