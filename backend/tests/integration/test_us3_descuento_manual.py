"""T032 — integración US3: Escenarios 3, 4 y 5 de quickstart.md.

3: autorización obligatoria sin excepción por monto.
4: descuento autorizado bajo margen mínimo se marca sin bloquear la venta.
5: cierre del ciclo de revisión.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def _venta_con_linea(client, e, auth, cantidad=3):
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
            json={"product_id": e["product_id"], "cantidad": cantidad},
            headers=auth,
        )
    ).json()
    return venta["venta_id"], venta["lineas"][0]["venta_detalle_id"]


async def test_escenario_3_autorizacion_obligatoria(client, escenario_pricing, auth_cajero):
    e = escenario_pricing
    venta_id, linea_id = await _venta_con_linea(client, e, auth_cajero)
    base = {
        "tipo": "monto",
        "valor": "0.20",
        "motivo": "match de competencia",
        "empleado_aplica_id": e["cajero_id"],
    }
    url = f"/api/ventas/{venta_id}/lineas/{linea_id}/descuento"

    r1 = await client.post(
        url, json={**base, "empleado_autoriza_id": e["cajero_id"]}, headers=auth_cajero
    )
    assert r1.status_code == 403
    r2 = await client.post(
        url, json={**base, "empleado_autoriza_id": e["jefe_ti_id"]}, headers=auth_cajero
    )
    assert r2.status_code == 403
    r3 = await client.post(
        url, json={**base, "empleado_autoriza_id": e["encargado_id"]}, headers=auth_cajero
    )
    assert r3.status_code == 200, r3.text


async def test_escenario_4_y_5_marca_sin_bloquear_y_cierra_ciclo(
    client, escenario_pricing, auth_cajero, auth_pricing_jc
):
    e = escenario_pricing
    venta_id, linea_id = await _venta_con_linea(client, e, auth_cajero, cantidad=3)

    # descuento grande: precio 2.50 → 1.00/ud (costo) → margen 0% < objetivo efectivo (8%)
    resp = await client.post(
        f"/api/ventas/{venta_id}/lineas/{linea_id}/descuento",
        json={
            "tipo": "monto",
            "valor": "4.50",
            "motivo": "liquidación de temporada",
            "empleado_aplica_id": e["cajero_id"],
            "empleado_autoriza_id": e["encargado_id"],
        },
        headers=auth_cajero,
    )
    assert resp.status_code == 200
    assert resp.json()["lineas"][0]["margen_bajo_minimo"] is True

    # la venta se confirma igual (la autorización no depende del resultado de margen)
    confirm = await client.post(
        f"/api/ventas/{venta_id}/confirmar",
        json={"medio_pago_id": e["medio_efectivo"]},
        headers=auth_cajero,
    )
    assert confirm.status_code == 200, confirm.text

    diario = (
        await client.get(
            f"/api/pricing/margen-bajo?tienda_id={e['tienda_id']}&revisado=false",
            headers=auth_pricing_jc,
        )
    ).json()
    assert any(i["venta_detalle_id"] == linea_id for i in diario["items"])

    # Escenario 5: registrar acción correctiva → sale de pendientes
    rev = await client.post(
        f"/api/pricing/margen-bajo/{linea_id}/revision",
        json={"accion_correctiva": "Ajuste aprobado por dirección comercial."},
        headers=auth_pricing_jc,
    )
    assert rev.status_code == 200, rev.text
    pendientes = (
        await client.get(
            f"/api/pricing/margen-bajo?tienda_id={e['tienda_id']}&revisado=false",
            headers=auth_pricing_jc,
        )
    ).json()
    assert not any(i["venta_detalle_id"] == linea_id for i in pendientes["items"])
