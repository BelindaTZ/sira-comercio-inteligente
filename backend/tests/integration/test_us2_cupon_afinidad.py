"""T021 + T022 — integración US2: Escenario 3 de quickstart.md.

Una venta de un cliente con consentimiento que compra el antecedente de una regla
vigente sin el consecuente dispara un cupón de afinidad; no se duplica dentro de
la ventana de vigencia; un cliente sin consentimiento no recibe nada; la tasa de
redención se calcula separada de la de cupones por hito.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _venta_confirmada(client, e, auth, household_id, product_id):
    venta = (
        await client.post(
            "/api/ventas",
            json={
                "tienda_id": e["tienda_id"],
                "cajero_id": e["cajero_id"],
                "household_id": household_id,
            },
            headers=auth,
        )
    ).json()
    await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas",
        json={"product_id": product_id, "cantidad": 1},
        headers=auth,
    )
    confirm = await client.post(
        f"/api/ventas/{venta['venta_id']}/confirmar",
        json={"medio_pago_id": e["medio_efectivo"]},
        headers=auth,
    )
    assert confirm.status_code == 200, confirm.text
    return venta["venta_id"]


async def test_cupon_afinidad_ciclo_completo(
    client, escenario_promociones, auth_mkt, auth_cajero, db_session
):
    e = escenario_promociones
    await client.post("/api/promociones/reglas-afinidad/calcular", headers=auth_mkt)

    # compra A sin B → dispara el cupón para B
    await _venta_confirmada(client, e, auth_cajero, e["household_afin"], e["product_a"])

    cupones = (
        await client.get(
            f"/api/promociones/cupones-afinidad?household_id={e['household_afin']}",
            headers=auth_mkt,
        )
    ).json()
    assert len(cupones) == 1
    assert cupones[0]["regla_afinidad_id"] is not None
    assert cupones[0]["product_id_ofrecido"] == e["product_b"]

    # segunda compra igual, dentro de la vigencia → NO se duplica (FR-007)
    await _venta_confirmada(client, e, auth_cajero, e["household_afin"], e["product_a"])
    cupones = (
        await client.get(
            f"/api/promociones/cupones-afinidad?household_id={e['household_afin']}",
            headers=auth_mkt,
        )
    ).json()
    assert len(cupones) == 1

    # tasa de redención de afinidad (separada de la de hito de 002)
    tasa = (
        await client.get("/api/promociones/cupones-afinidad/tasa-redencion", headers=auth_mkt)
    ).json()
    assert tasa["enviados"] == 1
    assert tasa["redimidos"] == 0


async def test_cliente_sin_consentimiento_no_recibe_cupon(
    client, escenario_promociones, auth_mkt, auth_cajero, db_session
):
    e = escenario_promociones
    await client.post("/api/promociones/reglas-afinidad/calcular", headers=auth_mkt)

    sin_consent = await db_session.scalar(
        text(
            "INSERT INTO clientes (nombre, email, consentimiento_datos, activo) "
            "VALUES ('Sin Consent', 'nc@test.local', false, true) RETURNING household_id"
        )
    )
    await db_session.flush()

    await _venta_confirmada(client, e, auth_cajero, sin_consent, e["product_a"])
    cupones = (
        await client.get(
            f"/api/promociones/cupones-afinidad?household_id={sin_consent}", headers=auth_mkt
        )
    ).json()
    assert cupones == []
