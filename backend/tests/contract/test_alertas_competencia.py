"""T044 — contrato GET /api/pricing/competencia/alertas (FR-015, FR-016)."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_alerta_aparece_cuando_la_desviacion_supera_el_umbral(
    client, escenario_pricing, auth_pricing_jc
):
    e = escenario_pricing  # producto precio_base 2.50
    comp = await client.post(
        "/api/pricing/competidores",
        json={"nombre": "Competencia", "tipo": "supermercado"},
        headers=auth_pricing_jc,
    )
    competidor_id = comp.json()["competidor_id"]
    # 2.00 vs 2.50 → 20% de desviación, por encima del umbral por defecto (5%)
    await client.post(
        f"/api/pricing/productos/{e['product_id']}/precio-competencia",
        json={"competidor_id": competidor_id, "precio": "2.00"},
        headers=auth_pricing_jc,
    )
    await client.post("/api/_dev/jobs/alertas_competencia_semanal")

    alertas = (await client.get("/api/pricing/competencia/alertas", headers=auth_pricing_jc)).json()
    fila = next(a for a in alertas["items"] if a["product_id"] == e["product_id"])
    assert fila["fuente_captura"] == "manual"
    assert float(fila["desviacion_pct"]) == 20.0


async def test_producto_sin_dato_no_genera_alerta(client, escenario_pricing, auth_pricing_jc):
    # ningún precio_competencia registrado → el producto no aparece
    alertas = (await client.get("/api/pricing/competencia/alertas", headers=auth_pricing_jc)).json()
    assert all(a["product_id"] != escenario_pricing["product_id"] for a in alertas["items"])


async def test_umbral_configurable_por_query(client, escenario_pricing, auth_pricing_jc):
    e = escenario_pricing
    comp = await client.post(
        "/api/pricing/competidores",
        json={"nombre": "C2", "tipo": "tienda_barrio"},
        headers=auth_pricing_jc,
    )
    await client.post(
        f"/api/pricing/productos/{e['product_id']}/precio-competencia",
        json={"competidor_id": comp.json()["competidor_id"], "precio": "2.45"},  # 2% desviación
        headers=auth_pricing_jc,
    )
    con_umbral_alto = (
        await client.get("/api/pricing/competencia/alertas?umbral=5", headers=auth_pricing_jc)
    ).json()
    assert all(a["product_id"] != e["product_id"] for a in con_umbral_alto["items"])
    con_umbral_bajo = (
        await client.get("/api/pricing/competencia/alertas?umbral=1", headers=auth_pricing_jc)
    ).json()
    assert any(a["product_id"] == e["product_id"] for a in con_umbral_bajo["items"])
