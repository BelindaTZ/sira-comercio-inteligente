"""T043 — contrato de competidores y precio de referencia de competencia (FR-014).

El servidor SIEMPRE fija `fuente_captura = "manual"` y `registrado_por` = el
usuario autenticado, nunca desde el body.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_alta_de_competidor_y_captura_manual(client, escenario_pricing, auth_pricing_jc):
    e = escenario_pricing
    comp = await client.post(
        "/api/pricing/competidores",
        json={"nombre": "Tía", "tipo": "supermercado", "ciudad": "Quito"},
        headers=auth_pricing_jc,
    )
    assert comp.status_code == 201, comp.text
    competidor_id = comp.json()["competidor_id"]

    listado = (await client.get("/api/pricing/competidores", headers=auth_pricing_jc)).json()
    assert any(c["competidor_id"] == competidor_id for c in listado)

    captura = await client.post(
        f"/api/pricing/productos/{e['product_id']}/precio-competencia",
        json={
            "competidor_id": competidor_id,
            "precio": "2.20",
            "es_promocional": True,
            # aunque el cliente intente forzar otra fuente, el servidor la ignora
            "fuente_captura": "sintetico",
        },
        headers=auth_pricing_jc,
    )
    assert captura.status_code == 201, captura.text
    body = captura.json()
    assert body["fuente_captura"] == "manual"
    assert body["registrado_por"] == e["jefe_comercial_id"]
    assert body["es_promocional"] is True

    historial = (
        await client.get(
            f"/api/pricing/productos/{e['product_id']}/precio-competencia",
            headers=auth_pricing_jc,
        )
    ).json()
    assert historial[0]["precio"] == "2.20"
    assert historial[0]["fuente_captura"] == "manual"


async def test_competidor_inexistente_da_404(client, escenario_pricing, auth_pricing_jc):
    e = escenario_pricing
    resp = await client.post(
        f"/api/pricing/productos/{e['product_id']}/precio-competencia",
        json={"competidor_id": 999999, "precio": "1.00"},
        headers=auth_pricing_jc,
    )
    assert resp.status_code == 404, resp.text


async def test_cajero_no_puede_registrar_competidor(client, escenario_pricing, auth_cajero):
    resp = await client.post(
        "/api/pricing/competidores",
        json={"nombre": "X", "tipo": "supermercado"},
        headers=auth_cajero,
    )
    assert resp.status_code == 403, resp.text
