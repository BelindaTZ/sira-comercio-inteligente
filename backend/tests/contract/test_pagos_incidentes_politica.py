"""Contrato de incidentes de seguridad de pago y política de seguridad
(`contracts/pagos-seguridad.md`, FR-008 a FR-014)."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_ciclo_incidente_y_conteo(
    client, escenario_pagos, auth_caja_ti, auth_caja_finanzas
):
    e = escenario_pagos
    abrir = await client.post(
        "/api/caja/incidentes-seguridad-pago",
        json={"datafono_id": e["datafono_viejo"], "descripcion": "Posible clonación"},
        headers=auth_caja_ti,
    )
    assert abrir.status_code == 201, abrir.text
    assert abrir.json()["estado"] == "abierto"
    inc = abrir.json()["incidente_seguridad_id"]

    salto = await client.patch(
        f"/api/caja/incidentes-seguridad-pago/{inc}/transicionar",
        json={"estado_nuevo": "cerrado"},
        headers=auth_caja_ti,
    )
    assert salto.status_code == 409, salto.text  # no se puede saltar en_investigacion

    a_invest = await client.patch(
        f"/api/caja/incidentes-seguridad-pago/{inc}/transicionar",
        json={"estado_nuevo": "en_investigacion"},
        headers=auth_caja_ti,
    )
    assert a_invest.status_code == 200 and a_invest.json()["estado"] == "en_investigacion"
    assert a_invest.json()["actualizado_por"] == e["encargado_id"]

    cerrar = await client.patch(
        f"/api/caja/incidentes-seguridad-pago/{inc}/transicionar",
        json={"estado_nuevo": "cerrado"},
        headers=auth_caja_ti,
    )
    assert cerrar.status_code == 200 and cerrar.json()["estado"] == "cerrado"

    conteo = await client.get(
        "/api/caja/incidentes-seguridad-pago/conteo", headers=auth_caja_finanzas
    )
    assert conteo.status_code == 200, conteo.text
    assert conteo.json()["total"] >= 1


async def test_incidente_sin_datafono_se_acepta(client, escenario_pagos, auth_caja_ti):
    resp = await client.post(
        "/api/caja/incidentes-seguridad-pago",
        json={"descripcion": "Reporte genérico del banco, sin datáfono identificado"},
        headers=auth_caja_ti,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["datafono_id"] is None


async def test_politica_versionada(
    client, escenario_pagos, auth_caja_ti, auth_encargado, auth_caja_finanzas
):
    v1 = await client.put(
        "/api/caja/politica-seguridad-pagos",
        json={"texto": "Política v1 — lineamientos base"},
        headers=auth_caja_ti,
    )
    assert v1.status_code == 201, v1.text
    politica_v1 = v1.json()["politica_id"]

    consulta = await client.get("/api/caja/politica-seguridad-pagos", headers=auth_encargado)
    assert consulta.status_code == 200
    assert consulta.json()["texto"] == "Política v1 — lineamientos base"

    v2 = await client.put(
        "/api/caja/politica-seguridad-pagos",
        json={"texto": "Política v2 — endurecida"},
        headers=auth_caja_ti,
    )
    assert v2.status_code == 201

    # la versión anterior sigue consultable por su id
    vieja = await client.get(
        f"/api/caja/politica-seguridad-pagos/{politica_v1}", headers=auth_caja_finanzas
    )
    assert vieja.status_code == 200 and vieja.json()["texto"] == "Política v1 — lineamientos base"

    vigente = await client.get("/api/caja/politica-seguridad-pagos", headers=auth_encargado)
    assert vigente.json()["texto"] == "Política v2 — endurecida"


async def test_encargado_no_registra_incidente_ni_define_politica(
    client, escenario_pagos, auth_encargado
):
    r1 = await client.post(
        "/api/caja/incidentes-seguridad-pago",
        json={"descripcion": "x"},
        headers=auth_encargado,
    )
    assert r1.status_code == 403, r1.text
    r2 = await client.put(
        "/api/caja/politica-seguridad-pagos", json={"texto": "x"}, headers=auth_encargado
    )
    assert r2.status_code == 403, r2.text
