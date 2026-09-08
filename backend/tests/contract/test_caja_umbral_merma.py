"""Contrato del umbral de merma y el seguimiento semanal
(`contracts/caja-mermas-fraude.md`, FR-017 a FR-019)."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_jefe_operaciones_define_umbral_y_encargado_lo_consulta(
    client, escenario_caja, auth_caja_ops, auth_encargado
):
    put = await client.put(
        "/api/caja/umbral-merma/TEST CAT",
        json={"porcentaje_umbral": "5.0"},
        headers=auth_caja_ops,
    )
    assert put.status_code == 200, put.text
    assert put.json()["product_category"] == "TEST CAT"

    # upsert: segunda llamada actualiza, no duplica
    put2 = await client.put(
        "/api/caja/umbral-merma/TEST CAT",
        json={"porcentaje_umbral": "7.5"},
        headers=auth_caja_ops,
    )
    assert put2.status_code == 200
    assert float(put2.json()["porcentaje_umbral"]) == 7.5

    lista = await client.get("/api/caja/umbral-merma", headers=auth_encargado)
    assert lista.status_code == 200
    assert [u for u in lista.json() if u["product_category"] == "TEST CAT"]


async def test_encargado_no_define_umbral(client, escenario_caja, auth_encargado):
    resp = await client.put(
        "/api/caja/umbral-merma/TEST CAT",
        json={"porcentaje_umbral": "5.0"},
        headers=auth_encargado,
    )
    assert resp.status_code == 403, resp.text


async def test_seguimiento_semanal_sin_umbrales_es_vacio(client, escenario_caja, auth_encargado):
    e = escenario_caja
    resp = await client.get(
        f"/api/caja/tiendas/{e['tienda_id']}/seguimiento-merma-semanal",
        params={"semana": 10},
        headers=auth_encargado,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


async def test_umbral_invalido_es_rechazado(client, escenario_caja, auth_caja_ops):
    resp = await client.put(
        "/api/caja/umbral-merma/TEST CAT",
        json={"porcentaje_umbral": "0"},
        headers=auth_caja_ops,
    )
    assert resp.status_code == 422, resp.text
