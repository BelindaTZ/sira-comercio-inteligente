"""T011 — contrato de disponibilidad diaria de datáfonos y advertencia de cobro
(`contracts/pagos-seguridad.md`, FR-001 a FR-004). Las rutas del contrato bajo
`/api/finanzas/...` se implementan bajo `/api/caja/...` (nomenclatura fijada por 006).
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_fuera_servicio_y_restablecer_con_reevaluacion(
    client, escenario_pagos, auth_encargado, auth_cajero
):
    e = escenario_pagos

    fuera = await client.patch(
        f"/api/caja/datafonos/{e['datafono_viejo']}/fuera-servicio",
        json={"motivo": "No lee chip, error persistente"},
        headers=auth_encargado,
    )
    assert fuera.status_code == 200, fuera.text
    assert fuera.json()["estado"] == "fuera_servicio"
    assert fuera.json()["motivo_fuera_servicio"] == "No lee chip, error persistente"

    # el motivo es obligatorio
    sin_motivo = await client.patch(
        f"/api/caja/datafonos/{e['datafono_nuevo']}/fuera-servicio", headers=auth_encargado
    )
    assert sin_motivo.status_code == 422, sin_motivo.text

    # doble marca → 409
    otra = await client.patch(
        f"/api/caja/datafonos/{e['datafono_viejo']}/fuera-servicio",
        json={"motivo": "otra vez"},
        headers=auth_encargado,
    )
    assert otra.status_code == 409, otra.text

    disp = await client.get(
        f"/api/ventas/cajas/{e['caja_1']}/datafono-disponible", headers=auth_cajero
    )
    assert disp.status_code == 200, disp.text
    assert disp.json()["disponible"] is False

    # restablecer un datáfono cuyo firmware (2.9.0) NO cumple el estándar (3.0.0)
    rest = await client.patch(
        f"/api/caja/datafonos/{e['datafono_viejo']}/restablecer", headers=auth_encargado
    )
    assert rest.status_code == 200, rest.text
    assert rest.json()["estado"] == "requiere_actualizacion"  # no 'activo'

    # al restablecer se limpia el motivo
    listado = await client.get(
        "/api/caja/datafonos", params={"estado": "requiere_actualizacion"}, headers=auth_encargado
    )
    fila = next(d for d in listado.json() if d["datafono_id"] == e["datafono_viejo"])
    assert fila["motivo_fuera_servicio"] is None


async def test_restablecer_datafono_conforme_queda_activo(client, escenario_pagos, auth_encargado):
    e = escenario_pagos
    await client.patch(
        f"/api/caja/datafonos/{e['datafono_nuevo']}/fuera-servicio",
        json={"motivo": "mantención preventiva"},
        headers=auth_encargado,
    )
    rest = await client.patch(
        f"/api/caja/datafonos/{e['datafono_nuevo']}/restablecer", headers=auth_encargado
    )
    assert rest.status_code == 200 and rest.json()["estado"] == "activo"


async def test_restablecer_un_datafono_operativo_da_409(client, escenario_pagos, auth_encargado):
    e = escenario_pagos
    resp = await client.patch(
        f"/api/caja/datafonos/{e['datafono_nuevo']}/restablecer", headers=auth_encargado
    )
    assert resp.status_code == 409, resp.text


async def test_cajero_no_marca_datafonos(client, escenario_pagos, auth_cajero):
    e = escenario_pagos
    resp = await client.patch(
        f"/api/caja/datafonos/{e['datafono_viejo']}/fuera-servicio",
        json={"motivo": "x"},
        headers=auth_cajero,
    )
    assert resp.status_code == 403, resp.text
