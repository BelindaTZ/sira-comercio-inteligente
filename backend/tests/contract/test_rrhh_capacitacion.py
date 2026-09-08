"""T021 — contrato de capacitación (feature 011, `contracts/recursos-humanos.md`,
FR-003 a FR-005).
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_programar_completar_y_consultar_cumplimiento(client, escenario_rrhh, auth_jefe_rrhh):
    e = escenario_rrhh

    prog = await client.post(
        "/api/rrhh/capacitaciones",
        json={"nombre": "Alertas de IA", "role_ids": [e["rol_cajero_id"]]},
        headers=auth_jefe_rrhh,
    )
    assert prog.status_code == 201, prog.text
    cap_id = prog.json()["capacitacion_id"]
    assert prog.json()["empleados_asignados"] >= 2

    completar = await client.patch(
        f"/api/rrhh/empleado-capacitacion/{e['cajero_a1']}/{cap_id}/completar",
        json={"fecha_completado": "2026-05-10"},
        headers=auth_jefe_rrhh,
    )
    assert completar.status_code == 200, completar.text
    assert completar.json()["fecha_completado"] == "2026-05-10"

    cumplimiento = await client.get(
        f"/api/rrhh/tiendas/{e['tienda_a']}/cumplimiento-capacitacion",
        headers={"Authorization": f"Bearer {e['token_encargado_a']}"},
    )
    assert cumplimiento.status_code == 200, cumplimiento.text
    filas = {f["empleado_id"]: f for f in cumplimiento.json()}
    assert filas[e["cajero_a1"]]["fecha_completado"] == "2026-05-10"
    assert filas[e["cajero_a2"]]["fecha_completado"] is None
    # ningún empleado de la tienda B aparece en el cumplimiento de la tienda A
    assert e["cajero_b1"] not in filas


async def test_encargado_no_ve_cumplimiento_de_otra_tienda(client, escenario_rrhh):
    e = escenario_rrhh
    resp = await client.get(
        f"/api/rrhh/tiendas/{e['tienda_a']}/cumplimiento-capacitacion",
        headers={"Authorization": f"Bearer {e['token_encargado_b']}"},
    )
    assert resp.status_code == 403


async def test_completar_capacitacion_no_asignada_es_404(client, escenario_rrhh, auth_jefe_rrhh):
    e = escenario_rrhh
    prog = await client.post(
        "/api/rrhh/capacitaciones",
        json={"nombre": "Solo B", "role_ids": [e["rol_cajero_id"]]},
        headers=auth_jefe_rrhh,
    )
    cap_id = prog.json()["capacitacion_id"]
    resp = await client.patch(
        f"/api/rrhh/empleado-capacitacion/{e['cajero_a_sin_cuenta']}/{cap_id}/completar",
        json={"fecha_completado": "2026-05-10"},
        headers=auth_jefe_rrhh,
    )
    assert resp.status_code == 404
