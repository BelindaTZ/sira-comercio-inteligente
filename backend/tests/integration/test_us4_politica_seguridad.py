"""Integración US4: Escenario 4 de quickstart.md — política de seguridad de pagos
versionada, consultable por Encargado de Tienda; la versión anterior sigue
consultable por su id tras publicar una nueva.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_politica_versionada_de_punta_a_punta(
    client, escenario_pagos, auth_caja_ti, auth_encargado, auth_caja_finanzas
):
    v1 = await client.put(
        "/api/caja/politica-seguridad-pagos",
        json={"texto": "Versión 1: lineamientos PCI base"},
        headers=auth_caja_ti,
    )
    assert v1.status_code == 201
    id_v1 = v1.json()["politica_id"]

    consulta = await client.get("/api/caja/politica-seguridad-pagos", headers=auth_encargado)
    assert consulta.status_code == 200
    assert consulta.json()["texto"] == "Versión 1: lineamientos PCI base"

    v2 = await client.put(
        "/api/caja/politica-seguridad-pagos",
        json={"texto": "Versión 2: se agrega rotación de llaves"},
        headers=auth_caja_ti,
    )
    assert v2.status_code == 201

    vieja = await client.get(
        f"/api/caja/politica-seguridad-pagos/{id_v1}", headers=auth_caja_finanzas
    )
    assert vieja.status_code == 200
    assert vieja.json()["texto"] == "Versión 1: lineamientos PCI base"

    vigente = await client.get("/api/caja/politica-seguridad-pagos", headers=auth_caja_finanzas)
    assert vigente.json()["politica_id"] == v2.json()["politica_id"]
