"""Contrato del reporte de patrones, incidentes de fraude y protocolo de
escalamiento (`contracts/caja-mermas-fraude.md`, FR-009 a FR-016)."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_reporte_diferencias_solo_para_jefe_finanzas(
    client, escenario_caja, auth_caja_finanzas, auth_cajero
):
    ok = await client.get(
        "/api/caja/reporte-diferencias", params={"mes": 9, "anio": 2026}, headers=auth_caja_finanzas
    )
    assert ok.status_code == 200, ok.text
    assert "cuadres" in ok.json() and "ajustes_senalados" in ok.json()

    no = await client.get(
        "/api/caja/reporte-diferencias", params={"mes": 9, "anio": 2026}, headers=auth_cajero
    )
    assert no.status_code == 403, no.text


async def test_ciclo_incidente_abierto_en_revision_cerrado(
    client, escenario_caja, auth_caja_finanzas, auth_encargado, db_session
):
    e = escenario_caja
    await db_session.execute(
        text("INSERT INTO protocolo_escalamiento (texto, definido_por) VALUES ('P', :emp)"),
        {"emp": e["cajero_id"]},
    )
    await db_session.flush()

    abrir = await client.post(
        "/api/caja/incidentes-fraude",
        json={"empleado_id": e["cajero_id"], "descripcion": "Diferencias repetidas"},
        headers=auth_caja_finanzas,
    )
    assert abrir.status_code == 201, abrir.text
    incidente_id = abrir.json()["incidente_id"]
    assert abrir.json()["estado"] == "abierto"

    # el listado enriquece con el nombre del empleado involucrado
    listado = await client.get("/api/caja/incidentes-fraude", headers=auth_caja_finanzas)
    fila = next(i for i in listado.json() if i["incidente_id"] == incidente_id)
    assert "empleado_nombre" in fila

    # cerrar directamente un incidente abierto → 409
    directo = await client.patch(
        f"/api/caja/incidentes-fraude/{incidente_id}/cerrar",
        json={"resultado": "descartado"},
        headers=auth_caja_finanzas,
    )
    assert directo.status_code == 409, directo.text

    aplicar = await client.patch(
        f"/api/caja/incidentes-fraude/{incidente_id}/aplicar-protocolo",
        json={"acciones_tomadas": "Se revisó el CCTV"},
        headers=auth_encargado,
    )
    assert aplicar.status_code == 200 and aplicar.json()["estado"] == "en_revision"
    assert aplicar.json()["actualizado_por"] == e["encargado_id"]

    cerrar = await client.patch(
        f"/api/caja/incidentes-fraude/{incidente_id}/cerrar",
        json={"resultado": "descartado"},
        headers=auth_caja_finanzas,
    )
    assert cerrar.status_code == 200 and cerrar.json()["estado"] == "cerrado"
    assert cerrar.json()["resultado"] == "descartado"


async def test_protocolo_vigente_consultable_por_encargado(
    client, escenario_caja, auth_caja_finanzas, auth_encargado
):
    put = await client.put(
        "/api/caja/protocolo-escalamiento",
        json={"texto": "Protocolo actualizado 2026"},
        headers=auth_caja_finanzas,
    )
    assert put.status_code == 201, put.text

    get = await client.get("/api/caja/protocolo-escalamiento", headers=auth_encargado)
    assert get.status_code == 200
    assert get.json()["texto"] == "Protocolo actualizado 2026"


async def test_encargado_no_define_protocolo(client, escenario_caja, auth_encargado):
    resp = await client.put(
        "/api/caja/protocolo-escalamiento", json={"texto": "x"}, headers=auth_encargado
    )
    assert resp.status_code == 403, resp.text


async def test_historial_protocolo_lista_versiones(
    client, escenario_caja, auth_caja_finanzas, auth_encargado
):
    for txt in ("Protocolo v1", "Protocolo v2", "Protocolo v3"):
        await client.put(
            "/api/caja/protocolo-escalamiento", json={"texto": txt}, headers=auth_caja_finanzas
        )
    hist = await client.get("/api/caja/protocolo-escalamiento/historial", headers=auth_encargado)
    assert hist.status_code == 200, hist.text
    textos = [v["texto"] for v in hist.json()]
    assert textos[:3] == ["Protocolo v3", "Protocolo v2", "Protocolo v1"]  # más reciente primero
