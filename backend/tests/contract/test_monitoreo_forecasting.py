"""T029 — contrato GET /api/forecasting/modelos/{id}/monitoreo y .../monitoreo/alertas."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_monitoreo_de_modelo_inexistente_da_404(client, escenario_forecasting, auth_jefe_ti):
    resp = await client.get("/api/forecasting/modelos/999999/monitoreo", headers=auth_jefe_ti)
    assert resp.status_code == 404, resp.text


async def test_monitoreo_vacio_de_modelo_recien_entrenado(
    client, escenario_forecasting, auth_jefe_ti
):
    m = (await client.post("/api/forecasting/modelos/entrenar", headers=auth_jefe_ti)).json()[
        "modelo_id"
    ]
    hist = (
        await client.get(f"/api/forecasting/modelos/{m}/monitoreo", headers=auth_jefe_ti)
    ).json()
    assert hist == []


async def test_alertas_monitoreo_sin_datos_es_lista_vacia(
    client, escenario_forecasting, auth_jefe_ti
):
    resp = await client.get("/api/forecasting/monitoreo/alertas", headers=auth_jefe_ti)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_cajero_no_puede_ver_monitoreo(client, escenario_forecasting, auth_cajero):
    resp = await client.get("/api/forecasting/monitoreo/alertas", headers=auth_cajero)
    assert resp.status_code == 403, resp.text
