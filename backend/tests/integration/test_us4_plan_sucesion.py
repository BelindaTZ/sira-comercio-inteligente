"""T030 (integración) — US4 (feature 011): Escenario 4 de quickstart.md.

Registrar candidato para un puesto crítico → aparece con `sin_cobertura: false`;
un segundo puesto crítico sin candidato aparece con `sin_cobertura: true`.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_plan_sucesion_y_senal_de_cobertura(client, escenario_rrhh, auth_jefe_rrhh):
    e = escenario_rrhh

    assert (
        await client.post(
            "/api/rrhh/plan-sucesion",
            json={
                "puesto_id": e["puesto_critico_id"],
                "empleado_candidato_id": e["cajero_a1"],
            },
            headers=auth_jefe_rrhh,
        )
    ).status_code == 201

    assert (
        await client.patch(
            f"/api/rrhh/puestos/{e['puesto_normal_id']}/critico",
            json={"es_critico": True},
            headers=auth_jefe_rrhh,
        )
    ).status_code == 200

    cobertura = await client.get("/api/rrhh/plan-sucesion/cobertura", headers=auth_jefe_rrhh)
    assert cobertura.status_code == 200
    por_puesto = {p["puesto_id"]: p for p in cobertura.json()}

    assert por_puesto[e["puesto_critico_id"]]["sin_cobertura"] is False
    assert por_puesto[e["puesto_normal_id"]]["sin_cobertura"] is True
