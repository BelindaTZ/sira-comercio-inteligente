"""T011 + T030 — contrato RBAC del módulo Promociones (`contracts/promociones.md`)."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_cajero_no_puede_listar_reglas(client, escenario_promociones, auth_cajero):
    resp = await client.get("/api/promociones/reglas-afinidad", headers=auth_cajero)
    assert resp.status_code == 403, resp.text


async def test_cajero_si_puede_consultar_recomendacion(client, escenario_promociones, auth_cajero):
    e = escenario_promociones
    resp = await client.get(
        f"/api/promociones/recomendacion-cross-sell?product_ids={e['product_a']}",
        headers=auth_cajero,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["recomendacion_disponible"] is False  # aún sin reglas calculadas


async def test_jefe_marketing_no_ejecuta_candidatos_de_liquidacion(
    client, escenario_promociones, auth_mkt
):
    resp = await client.post("/api/promociones/liquidacion/candidatos/1/ejecutar", headers=auth_mkt)
    assert resp.status_code == 403, resp.text


async def test_desactivar_regla_inexistente_da_404(client, escenario_promociones, auth_mkt):
    resp = await client.post("/api/promociones/reglas-afinidad/999999/desactivar", headers=auth_mkt)
    assert resp.status_code == 404, resp.text


async def test_ejecutar_candidato_inexistente_da_404(client, escenario_promociones, auth_encargado):
    resp = await client.post(
        "/api/promociones/liquidacion/candidatos/999999/ejecutar", headers=auth_encargado
    )
    assert resp.status_code == 404, resp.text
