"""T031 — contrato GET /api/pricing/margen-bajo y POST .../revision (FR-011, FR-012)."""

import pytest

pytestmark = pytest.mark.asyncio


async def _linea_con_margen_bajo(client, e, auth_cajero):
    venta = (
        await client.post(
            "/api/ventas",
            json={"tienda_id": e["tienda_id"], "cajero_id": e["cajero_id"]},
            headers=auth_cajero,
        )
    ).json()
    venta = (
        await client.post(
            f"/api/ventas/{venta['venta_id']}/lineas",
            json={"product_id": e["product_id"], "cantidad": 2},
            headers=auth_cajero,
        )
    ).json()
    linea_id = venta["lineas"][0]["venta_detalle_id"]
    resp = await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas/{linea_id}/descuento",
        json={
            "tipo": "monto",
            "valor": "3.00",  # deja el precio a costo → margen 0% < objetivo efectivo
            "motivo": "liquidación",
            "empleado_aplica_id": e["cajero_id"],
            "empleado_autoriza_id": e["encargado_id"],
        },
        headers=auth_cajero,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["lineas"][0]["margen_bajo_minimo"] is True
    return venta["venta_id"], linea_id


async def test_listado_y_cierre_del_ciclo_de_revision(
    client, escenario_pricing, auth_cajero, auth_pricing_jc
):
    e = escenario_pricing
    _venta_id, linea_id = await _linea_con_margen_bajo(client, e, auth_cajero)

    # consolidado (sin tienda_id) — vista de Jefe_Comercial
    consolidado = (await client.get("/api/pricing/margen-bajo", headers=auth_pricing_jc)).json()
    assert any(item["venta_detalle_id"] == linea_id for item in consolidado["items"])

    # listado diario de una tienda
    diario = (
        await client.get(
            f"/api/pricing/margen-bajo?tienda_id={e['tienda_id']}", headers=auth_pricing_jc
        )
    ).json()
    assert any(item["venta_detalle_id"] == linea_id for item in diario["items"])

    # pendientes: aparece
    pendientes = (
        await client.get("/api/pricing/margen-bajo?revisado=false", headers=auth_pricing_jc)
    ).json()
    assert any(i["venta_detalle_id"] == linea_id for i in pendientes["items"])

    # registrar la acción correctiva
    rev = await client.post(
        f"/api/pricing/margen-bajo/{linea_id}/revision",
        json={"accion_correctiva": "Revisado con el cajero; precio corregido."},
        headers=auth_pricing_jc,
    )
    assert rev.status_code == 200, rev.text

    # ya no está pendiente, sí en revisados
    pendientes = (
        await client.get("/api/pricing/margen-bajo?revisado=false", headers=auth_pricing_jc)
    ).json()
    assert not any(i["venta_detalle_id"] == linea_id for i in pendientes["items"])
    revisados = (
        await client.get("/api/pricing/margen-bajo?revisado=true", headers=auth_pricing_jc)
    ).json()
    fila = next(i for i in revisados["items"] if i["venta_detalle_id"] == linea_id)
    assert fila["accion_correctiva"].startswith("Revisado")


async def test_revision_sobre_linea_no_marcada_da_422(
    client, escenario_pricing, auth_cajero, auth_pricing_jc
):
    e = escenario_pricing
    venta = (
        await client.post(
            "/api/ventas",
            json={"tienda_id": e["tienda_id"], "cajero_id": e["cajero_id"]},
            headers=auth_cajero,
        )
    ).json()
    venta = (
        await client.post(
            f"/api/ventas/{venta['venta_id']}/lineas",
            json={"product_id": e["product_id"], "cantidad": 1},
            headers=auth_cajero,
        )
    ).json()
    linea_id = venta["lineas"][0]["venta_detalle_id"]
    resp = await client.post(
        f"/api/pricing/margen-bajo/{linea_id}/revision",
        json={"accion_correctiva": "no aplica"},
        headers=auth_pricing_jc,
    )
    assert resp.status_code == 422, resp.text
