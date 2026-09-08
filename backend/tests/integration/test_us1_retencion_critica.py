"""T010 — integración US1 (feature 011): Escenario 1 de quickstart.md.

Marcar puesto crítico → registrar acción de retención → consultar en cualquier
momento; y la retención para un empleado en un puesto NO crítico se permite igual.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_retencion_de_roles_criticos(client, escenario_rrhh, auth_jefe_rrhh):
    e = escenario_rrhh

    assert (
        await client.patch(
            f"/api/rrhh/puestos/{e['puesto_normal_id']}/critico",
            json={"es_critico": True},
            headers=auth_jefe_rrhh,
        )
    ).status_code == 200

    for empleado_id, desc in ((e["cajero_a1"], "Mentoría"), (e["cajero_a2"], "Bono")):
        assert (
            await client.post(
                "/api/rrhh/acciones-retencion",
                json={"empleado_id": empleado_id, "fecha": "2026-02-01", "descripcion": desc},
                headers=auth_jefe_rrhh,
            )
        ).status_code == 201

    # empleado en un puesto que quedó sin marcar como crítico
    assert (
        await client.post(
            "/api/rrhh/acciones-retencion",
            json={
                "empleado_id": e["empleado_critico_a"],
                "fecha": "2026-02-02",
                "descripcion": "Conversación de permanencia",
            },
            headers=auth_jefe_rrhh,
        )
    ).status_code == 201

    consulta = await client.get(
        f"/api/rrhh/empleados/{e['cajero_a1']}/acciones-retencion", headers=auth_jefe_rrhh
    )
    assert consulta.status_code == 200
    assert [a["descripcion"] for a in consulta.json()] == ["Mentoría"]
