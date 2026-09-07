"""T011 — integración US1: Escenario 1 de quickstart.md.

Ciclo completo: forzar entrenamiento → modelo pendiente con WAPE calculado → el
pronóstico NO se usa hasta aprobar → aprobar → queda vigente y consultable.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_ciclo_entrenar_aprobar_pronostico(client, escenario_forecasting, auth_jefe_ti):
    e = escenario_forecasting

    train = await client.post("/api/forecasting/modelos/entrenar", headers=auth_jefe_ti)
    assert train.status_code == 201, train.text
    body = train.json()
    assert body["entrenado"] is True
    assert body["pronosticos_generados"] > 0
    modelo_id = body["modelo_id"]

    pendientes = (
        await client.get("/api/forecasting/modelos?estado=pendiente", headers=auth_jefe_ti)
    ).json()
    fila = next(m for m in pendientes if m["modelo_id"] == modelo_id)
    assert fila["metrica_precision_validacion"] is not None  # WAPE ya calculado (SC-001)

    url_pron = (
        f"/api/forecasting/productos/{e['product_id']}/tiendas/{e['tienda_id']}/pronostico"
        f"?semana={e['semana_pronostico']}&anio={e['anio_historial']}"
    )
    # SC-002: sin modelo aprobado, el pronóstico pendiente no se usa
    antes = (await client.get(url_pron, headers=auth_jefe_ti)).json()
    assert antes["pronostico_disponible"] is False

    ok = await client.post(f"/api/forecasting/modelos/{modelo_id}/aprobar", headers=auth_jefe_ti)
    assert ok.status_code == 200, ok.text
    assert ok.json()["estado"] == "aprobado"

    despues = (await client.get(url_pron, headers=auth_jefe_ti)).json()
    assert despues["pronostico_disponible"] is True
    assert float(despues["cantidad_pronosticada"]) >= 0
    assert despues["modelo_id"] == modelo_id


async def test_cold_start_no_entra_al_pronostico(client, escenario_forecasting, auth_jefe_ti):
    e = escenario_forecasting
    train = await client.post("/api/forecasting/modelos/entrenar", headers=auth_jefe_ti)
    modelo_id = train.json()["modelo_id"]
    await client.post(f"/api/forecasting/modelos/{modelo_id}/aprobar", headers=auth_jefe_ti)

    # el producto con 3 semanas de historial no tiene pronóstico (FR-006)
    url = (
        f"/api/forecasting/productos/{e['product_cold']}/tiendas/{e['tienda_id']}/pronostico"
        f"?semana={e['semana_pronostico']}&anio={e['anio_historial']}"
    )
    assert (await client.get(url, headers=auth_jefe_ti)).json()["pronostico_disponible"] is False
