"""T021 — integración US2: Escenario 3 de quickstart.md.

Definir estándar → datáfono desactualizado aparece no conforme → se actualiza →
deja de aparecer, con `fecha_ultima_actualizacion` registrada.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_certificacion_y_actualizacion_de_datafono(client, escenario_caja, auth_caja_ti):
    e = escenario_caja

    definir = await client.put(
        "/api/caja/configuracion-seguridad-pagos",
        json={"version_minima_firmware": "3.2.0"},
        headers=auth_caja_ti,
    )
    assert definir.status_code == 201, definir.text

    vigente = await client.get(
        "/api/caja/configuracion-seguridad-pagos", headers=auth_caja_ti
    )
    assert vigente.json()["version_minima_firmware"] == "3.2.0"

    no_conformes = await client.get(
        "/api/caja/datafonos", params={"estado": "requiere_actualizacion"}, headers=auth_caja_ti
    )
    assert e["datafono_viejo"] in {d["datafono_id"] for d in no_conformes.json()}

    actualizar = await client.patch(
        f"/api/caja/datafonos/{e['datafono_viejo']}/actualizar",
        json={"version_firmware_nueva": "3.4.1"},
        headers=auth_caja_ti,
    )
    assert actualizar.status_code == 200, actualizar.text
    assert actualizar.json()["fecha_ultima_actualizacion"] is not None

    despues = await client.get(
        "/api/caja/datafonos", params={"estado": "requiere_actualizacion"}, headers=auth_caja_ti
    )
    assert e["datafono_viejo"] not in {d["datafono_id"] for d in despues.json()}
