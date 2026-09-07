"""T045 — integración US5: Escenario 6 de quickstart.md (las tres fuentes).

- manual sobre un producto sembrado (barcode sintético) → alerta.
- open_prices sobre un producto en vivo con barcode real (con y sin dato).
- ausencia total de dato → no genera alerta.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_captura_manual_genera_alerta(client, escenario_pricing, auth_pricing_jc):
    e = escenario_pricing
    comp = await client.post(
        "/api/pricing/competidores",
        json={"nombre": "Supermaxi", "tipo": "supermercado"},
        headers=auth_pricing_jc,
    )
    await client.post(
        f"/api/pricing/productos/{e['product_id']}/precio-competencia",
        json={"competidor_id": comp.json()["competidor_id"], "precio": "2.00"},
        headers=auth_pricing_jc,
    )
    await client.post("/api/_dev/jobs/alertas_competencia_semanal")
    alertas = (await client.get("/api/pricing/competencia/alertas", headers=auth_pricing_jc)).json()
    assert any(a["product_id"] == e["product_id"] for a in alertas["items"])


async def test_open_prices_en_vivo_con_y_sin_dato(
    client, escenario_pricing, auth_pricing_jc, db_session, monkeypatch
):
    # producto en vivo con barcode real (product_id >= 90_000_000)
    con_dato = await db_session.scalar(
        text("SELECT COALESCE(MAX(product_id),0)+1 FROM productos WHERE product_id >= 90000000")
    )
    con_dato = max(con_dato, 90000001)
    sin_dato = con_dato + 1
    for pid, bc in ((con_dato, "7501000111111"), (sin_dato, "7501000222222")):
        await db_session.execute(
            text(
                "INSERT INTO productos (product_id, product_category, product_type, costo, "
                "precio_base, codigo_barras) VALUES (:p, 'TEST CAT', 'EN VIVO', 1.00, 2.50, :bc)"
            ),
            {"p": pid, "bc": bc},
        )
    await db_session.flush()

    async def _fake(barcode: str):
        return 3.50 if barcode == "7501000111111" else None

    monkeypatch.setattr("src.integrations.open_prices_client.ultimo_precio_por_barcode", _fake)
    await client.post("/api/_dev/jobs/alertas_competencia_semanal")

    hist_con = (
        await client.get(
            f"/api/pricing/productos/{con_dato}/precio-competencia", headers=auth_pricing_jc
        )
    ).json()
    assert hist_con and hist_con[0]["fuente_captura"] == "open_prices"
    assert hist_con[0]["competidor_id"] is None

    hist_sin = (
        await client.get(
            f"/api/pricing/productos/{sin_dato}/precio-competencia", headers=auth_pricing_jc
        )
    ).json()
    assert hist_sin == []  # sin dato → no se inserta fila, no es un error


async def test_ausencia_total_no_genera_alerta(client, escenario_pricing, auth_pricing_jc):
    await client.post("/api/_dev/jobs/alertas_competencia_semanal")
    alertas = (await client.get("/api/pricing/competencia/alertas", headers=auth_pricing_jc)).json()
    assert all(a["product_id"] != escenario_pricing["product_id"] for a in alertas["items"])
