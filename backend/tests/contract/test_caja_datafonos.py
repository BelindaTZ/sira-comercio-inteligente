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
