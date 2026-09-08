"""T017 — integración US2 (feature 011): Escenario 2 de quickstart.md.

Programar capacitación → fan-out por rol → confirmar cumplimiento → el Encargado
de Tienda ve el estado de su personal (y sólo del suyo); un empleado sin cuenta
no aparece en el fan-out.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_capacitacion_con_fanout_y_cumplimiento_por_tienda(
    client, escenario_rrhh, auth_jefe_rrhh
):
    e = escenario_rrhh

    prog = await client.post(
        "/api/rrhh/capacitaciones",
        json={"nombre": "Nuevos dashboards", "role_ids": [e["rol_cajero_id"]]},
        headers=auth_jefe_rrhh,
    )
    assert prog.status_code == 201
    cap_id = prog.json()["capacitacion_id"]
    # A1 + A2 + B1 (con cuenta); el cajero A sin cuenta no entra
    assert prog.json()["empleados_asignados"] == 3

    assert (
        await client.patch(
            f"/api/rrhh/empleado-capacitacion/{e['cajero_a1']}/{cap_id}/completar",
            json={"fecha_completado": "2026-06-01"},
            headers=auth_jefe_rrhh,
        )
    ).status_code == 200

    vista_encargado = await client.get(
        f"/api/rrhh/tiendas/{e['tienda_a']}/cumplimiento-capacitacion",
        headers={"Authorization": f"Bearer {e['token_encargado_a']}"},
    )
    assert vista_encargado.status_code == 200
    filas = {f["empleado_id"]: f["fecha_completado"] for f in vista_encargado.json()}
    assert filas == {e["cajero_a1"]: "2026-06-01", e["cajero_a2"]: None}
    assert e["cajero_a_sin_cuenta"] not in filas
