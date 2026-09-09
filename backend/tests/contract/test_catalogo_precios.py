"""Contrato de la matriz de precios por canal + simulador de impacto (001, US4,
migración 0024): `GET/PATCH /catalogo/precios/canales`, `GET /catalogo/precios`,
`GET /catalogo/resumen`, `POST /catalogo/productos/{id}/simular-precio`.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_reglas_de_canal_y_edicion(client, escenario_pos, auth_jefe_comercial):
    r = await client.get("/api/catalogo/precios/canales", headers=auth_jefe_comercial)
    assert r.status_code == 200, r.text
    canales = {c["canal"]: c for c in r.json()}
    assert set(canales) == {"fisico", "delivery_app", "ecommerce"}
    assert float(canales["fisico"]["markup_pct"]) == 0
    assert float(canales["delivery_app"]["markup_pct"]) == 12

    up = await client.patch(
        "/api/catalogo/precios/canales/delivery_app",
        json={"markup_pct": "18"},
        headers=auth_jefe_comercial,
    )
    assert up.status_code == 200, up.text
    assert float(up.json()["markup_pct"]) == 18

    # el canal físico es la base: no admite recargo
    bad = await client.patch(
        "/api/catalogo/precios/canales/fisico",
        json={"markup_pct": "5"},
        headers=auth_jefe_comercial,
    )
    assert bad.status_code == 422, bad.text


async def test_canal_inexistente_es_404(client, escenario_pos, auth_jefe_comercial):
    r = await client.patch(
        "/api/catalogo/precios/canales/marketplace",
        json={"markup_pct": "10"},
        headers=auth_jefe_comercial,
    )
    assert r.status_code == 404


async def test_cajero_no_edita_reglas_de_canal(client, escenario_pos, auth_cajero):
    r = await client.patch(
        "/api/catalogo/precios/canales/delivery_app",
        json={"markup_pct": "20"},
        headers=auth_cajero,
    )
    assert r.status_code == 403


async def test_matriz_precios_trae_estado_de_margen(client, escenario_pos, auth_jefe_comercial):
    r = await client.get("/api/catalogo/precios?size=5", headers=auth_jefe_comercial)
    assert r.status_code == 200, r.text
    fila = next(f for f in r.json()["items"] if f["product_id"] == escenario_pos["product_id"])
    assert fila["estado_margen"] in {"optimo", "ajustado", "bajo", "sin_precio"}
    # producto de escenario_pos: costo 1.00 / precio 2.50 → margen 60%
    assert fila["margen_pct"] == pytest.approx(60.0, abs=0.1)


async def test_resumen_catalogo(client, escenario_pos, auth_jefe_comercial):
    r = await client.get("/api/catalogo/resumen", headers=auth_jefe_comercial)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("total_activos", "con_ean", "skus_bajo_margen", "margen_bruto_ponderado_pct"):
        assert k in d


async def test_simular_precio_sube_margen_al_subir_pvp(
    client, escenario_pos, auth_jefe_comercial
):
    r = await client.post(
        f"/api/catalogo/productos/{escenario_pos['product_id']}/simular-precio",
        json={"delta_pct": "6"},
        headers=auth_jefe_comercial,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert float(d["pvp_nuevo"]) > float(d["pvp_actual"])
    assert d["margen_nuevo_pct"] > d["margen_actual_pct"]
    assert "factor_elasticidad" in d

    # fuera del rango permitido (Field ge=-30, le=30)
    fuera = await client.post(
        f"/api/catalogo/productos/{escenario_pos['product_id']}/simular-precio",
        json={"delta_pct": "80"},
        headers=auth_jefe_comercial,
    )
    assert fuera.status_code == 422
