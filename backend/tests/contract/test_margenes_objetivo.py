"""T010 — contrato GET / PATCH /api/pricing/margenes (FR-001, FR-004)."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_patch_crea_y_lista_el_margen_objetivo(client, escenario_pricing, auth_pricing_jc):
    cat = "TEST CAT"
    resp = await client.patch(
        f"/api/pricing/margenes/{cat}",
        json={"margen_objetivo_pct": "20", "factor_sensibilidad": "0.3"},
        headers=auth_pricing_jc,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["margen_objetivo_pct"] == "20.00"
    assert resp.json()["factor_sensibilidad"] == "0.30"

    listado = (await client.get("/api/pricing/margenes", headers=auth_pricing_jc)).json()
    fila = next(m for m in listado if m["product_category"] == cat)
    assert fila["margen_objetivo_pct"] == "20.00"


async def test_factor_sensibilidad_fuera_de_rango_es_422(
    client, escenario_pricing, auth_pricing_jc
):
    resp = await client.patch(
        "/api/pricing/margenes/TEST CAT",
        json={"margen_objetivo_pct": "20", "factor_sensibilidad": "1.5"},
        headers=auth_pricing_jc,
    )
    assert resp.status_code == 422, resp.text


async def test_cajero_no_puede_editar_margen(client, escenario_pricing, auth_cajero):
    resp = await client.patch(
        "/api/pricing/margenes/TEST CAT",
        json={"margen_objetivo_pct": "20"},
        headers=auth_cajero,
    )
    assert resp.status_code == 403, resp.text


async def test_margen_efectivo_ancla_distinto_de_nicho(
    client, escenario_pricing, auth_pricing_jc, db_session
):
    from sqlalchemy import text

    e = escenario_pricing
    await client.patch(
        "/api/pricing/margenes/TEST CAT",
        json={"margen_objetivo_pct": "20"},
        headers=auth_pricing_jc,
    )
    # el producto de escenario_pos es nicho; creamos uno ancla en la misma categoría.
    ancla_id = await db_session.scalar(text("SELECT COALESCE(MAX(product_id),0)+1 FROM productos"))
    await db_session.execute(
        text(
            "INSERT INTO productos (product_id, product_category, product_type, costo, "
            "precio_base, es_ancla) VALUES (:p, 'TEST CAT', 'ANCLA', 1.00, 2.50, true)"
        ),
        {"p": ancla_id},
    )
    await db_session.flush()

    nicho = (
        await client.get(
            f"/api/pricing/productos/{e['product_id']}/margen-efectivo", headers=auth_pricing_jc
        )
    ).json()
    ancla = (
        await client.get(
            f"/api/pricing/productos/{ancla_id}/margen-efectivo", headers=auth_pricing_jc
        )
    ).json()
    assert ancla["margen_objetivo_efectivo"] != nicho["margen_objetivo_efectivo"]
    assert float(ancla["margen_objetivo_efectivo"]) < float(nicho["margen_objetivo_efectivo"])
