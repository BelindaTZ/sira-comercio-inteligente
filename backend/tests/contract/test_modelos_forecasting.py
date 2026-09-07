"""T010 — contrato POST /api/forecasting/modelos/{id}/aprobar y .../rechazar.

Transición de estado, `CHECK` de consistencia, y reemplazo automático del modelo
vigente anterior al aprobar uno nuevo (FR-004, FR-005, research.md Decisión 7).
"""

import pytest

pytestmark = pytest.mark.asyncio


async def _entrenar(client, auth) -> int:
    return (await client.post("/api/forecasting/modelos/entrenar", headers=auth)).json()[
        "modelo_id"
    ]


async def test_aprobar_reemplaza_al_vigente_anterior(client, escenario_forecasting, auth_jefe_ti):
    m1 = await _entrenar(client, auth_jefe_ti)
    r1 = await client.post(f"/api/forecasting/modelos/{m1}/aprobar", headers=auth_jefe_ti)
    assert r1.status_code == 200 and r1.json()["estado"] == "aprobado"

    m2 = await _entrenar(client, auth_jefe_ti)
    r2 = await client.post(
        f"/api/forecasting/modelos/{m2}/aprobar",
        json={"observaciones": "mejor WAPE"},
        headers=auth_jefe_ti,
    )
    assert r2.status_code == 200, r2.text

    # sólo m2 queda 'aprobado'; m1 pasa a 'reemplazado'
    aprobados = (
        await client.get("/api/forecasting/modelos?estado=aprobado", headers=auth_jefe_ti)
    ).json()
    assert [m["modelo_id"] for m in aprobados] == [m2]
    detalle_m1 = (await client.get(f"/api/forecasting/modelos/{m1}", headers=auth_jefe_ti)).json()
    assert detalle_m1["estado"] == "reemplazado"


async def test_rechazar_no_toca_al_vigente(client, escenario_forecasting, auth_jefe_ti):
    m1 = await _entrenar(client, auth_jefe_ti)
    await client.post(f"/api/forecasting/modelos/{m1}/aprobar", headers=auth_jefe_ti)

    m2 = await _entrenar(client, auth_jefe_ti)
    rech = await client.post(
        f"/api/forecasting/modelos/{m2}/rechazar",
        json={"observaciones": "precisión insuficiente"},
        headers=auth_jefe_ti,
    )
    assert rech.status_code == 200 and rech.json()["estado"] == "rechazado"

    aprobados = (
        await client.get("/api/forecasting/modelos?estado=aprobado", headers=auth_jefe_ti)
    ).json()
    assert [m["modelo_id"] for m in aprobados] == [m1]


async def test_rechazar_exige_motivo(client, escenario_forecasting, auth_jefe_ti):
    m = await _entrenar(client, auth_jefe_ti)
    resp = await client.post(
        f"/api/forecasting/modelos/{m}/rechazar", json={"observaciones": ""}, headers=auth_jefe_ti
    )
    assert resp.status_code == 422, resp.text


async def test_doble_resolucion_da_409(client, escenario_forecasting, auth_jefe_ti):
    m = await _entrenar(client, auth_jefe_ti)
    await client.post(f"/api/forecasting/modelos/{m}/aprobar", headers=auth_jefe_ti)
    otra = await client.post(f"/api/forecasting/modelos/{m}/aprobar", headers=auth_jefe_ti)
    assert otra.status_code == 409, otra.text


async def test_jefe_operaciones_no_puede_aprobar(
    client, escenario_forecasting, auth_jefe_ti, auth_jefe_ops_fc
):
    m = await _entrenar(client, auth_jefe_ti)
    resp = await client.post(f"/api/forecasting/modelos/{m}/aprobar", headers=auth_jefe_ops_fc)
    assert resp.status_code == 403, resp.text
