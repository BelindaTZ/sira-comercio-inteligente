"""Contrato de datáfonos y estándar de seguridad de pagos
(`contracts/caja-mermas-fraude.md`, FR-006 a FR-008)."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_definir_estandar_marca_datafonos_no_conformes(client, escenario_caja, auth_caja_ti):
    e = escenario_caja
    put = await client.put(
        "/api/caja/configuracion-seguridad-pagos",
        json={"version_minima_firmware": "3.2.0"},
        headers=auth_caja_ti,
    )
    assert put.status_code == 201, put.text

    listado = await client.get(
        "/api/caja/datafonos", params={"estado": "requiere_actualizacion"}, headers=auth_caja_ti
    )
    assert listado.status_code == 200, listado.text
    ids = {d["datafono_id"] for d in listado.json()}
    assert e["datafono_viejo"] in ids  # firmware 2.9.0 < 3.2.0
    assert e["datafono_nuevo"] not in ids  # firmware 3.2.0 == mínimo


async def test_actualizar_datafono_lo_vuelve_conforme(client, escenario_caja, auth_caja_ti):
    e = escenario_caja
    await client.put(
        "/api/caja/configuracion-seguridad-pagos",
        json={"version_minima_firmware": "3.2.0"},
        headers=auth_caja_ti,
    )
    resp = await client.patch(
        f"/api/caja/datafonos/{e['datafono_viejo']}/actualizar",
        json={"version_firmware_nueva": "3.2.0"},
        headers=auth_caja_ti,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "activo"
    assert resp.json()["fecha_ultima_actualizacion"] is not None

    # segundo intento sobre un datáfono ya conforme → 409
    otra = await client.patch(
        f"/api/caja/datafonos/{e['datafono_viejo']}/actualizar",
        json={"version_firmware_nueva": "3.3.0"},
        headers=auth_caja_ti,
    )
    assert otra.status_code == 409, otra.text


async def test_actualizar_datafono_inexistente_da_404(client, escenario_caja, auth_caja_ti):
    resp = await client.patch(
        "/api/caja/datafonos/999999/actualizar",
        json={"version_firmware_nueva": "9.9.9"},
        headers=auth_caja_ti,
    )
    assert resp.status_code == 404, resp.text


async def test_cajero_no_gestiona_datafonos(client, escenario_caja, auth_cajero):
    resp = await client.get("/api/caja/datafonos", headers=auth_cajero)
    assert resp.status_code == 403, resp.text


async def test_registrar_datafono_evalua_conformidad(client, escenario_caja, auth_caja_ti):
    """FR-006 — alta de un datáfono; el estado de conformidad se calcula contra el
    estándar vigente (FR-007), no se recibe del cliente."""
    e = escenario_caja
    await client.put(
        "/api/caja/configuracion-seguridad-pagos",
        json={"version_minima_firmware": "3.2.0"},
        headers=auth_caja_ti,
    )
    viejo = await client.post(
        "/api/caja/datafonos",
        json={"caja_id": e["caja_1"], "modelo": "PAX A80", "version_firmware": "2.5.0"},
        headers=auth_caja_ti,
    )
    assert viejo.status_code == 201, viejo.text
    assert viejo.json()["estado"] == "requiere_actualizacion"

    nuevo = await client.post(
        "/api/caja/datafonos",
        json={"caja_id": e["caja_2"], "modelo": "PAX A80", "version_firmware": "3.5.0"},
        headers=auth_caja_ti,
    )
    assert nuevo.json()["estado"] == "activo"

    inexistente = await client.post(
        "/api/caja/datafonos",
        json={"caja_id": 999999, "version_firmware": "3.5.0"},
        headers=auth_caja_ti,
    )
    assert inexistente.status_code == 404, inexistente.text


async def test_editar_datafono_recalcula_conformidad(client, escenario_caja, auth_caja_ti):
    """FR-006 — editar modelo/firmware recalcula el estado de conformidad."""
    e = escenario_caja
    await client.put(
        "/api/caja/configuracion-seguridad-pagos",
        json={"version_minima_firmware": "3.2.0"},
        headers=auth_caja_ti,
    )
    # `datafono_viejo` (2.9.0) quedó no conforme; subirle el firmware lo vuelve conforme
    resp = await client.patch(
        f"/api/caja/datafonos/{e['datafono_viejo']}",
        json={"version_firmware": "3.4.0", "modelo": "Verifone VX-680"},
        headers=auth_caja_ti,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "activo"
    assert resp.json()["modelo"] == "Verifone VX-680"


async def test_listar_cajas_de_la_red(client, escenario_caja, auth_caja_ti):
    e = escenario_caja
    resp = await client.get("/api/caja/cajas", headers=auth_caja_ti)
    assert resp.status_code == 200, resp.text
    ids = {c["caja_id"] for c in resp.json()}
    assert {e["caja_1"], e["caja_2"]} <= ids


async def test_cajero_no_registra_datafono(client, escenario_caja, auth_cajero):
    e = escenario_caja
    resp = await client.post(
        "/api/caja/datafonos",
        json={"caja_id": e["caja_1"], "version_firmware": "3.5.0"},
        headers=auth_cajero,
    )
    assert resp.status_code == 403, resp.text
