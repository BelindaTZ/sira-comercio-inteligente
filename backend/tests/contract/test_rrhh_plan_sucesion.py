"""T032 — contrato del plan de sucesión (feature 011,
`contracts/recursos-humanos.md`, FR-008/FR-009).
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_registrar_candidato_y_cobertura(client, escenario_rrhh, auth_jefe_rrhh):
    e = escenario_rrhh

    # puesto_critico_id ya viene marcado como crítico por el fixture
    alta = await client.post(
        "/api/rrhh/plan-sucesion",
        json={
            "puesto_id": e["puesto_critico_id"],
            "empleado_candidato_id": e["cajero_a2"],
        },
        headers=auth_jefe_rrhh,
    )
    assert alta.status_code == 201, alta.text

    # un segundo puesto crítico sin candidato
    otro = await client.patch(
        f"/api/rrhh/puestos/{e['puesto_normal_id']}/critico",
        json={"es_critico": True},
        headers=auth_jefe_rrhh,
    )
    assert otro.status_code == 200

    cobertura = await client.get("/api/rrhh/plan-sucesion/cobertura", headers=auth_jefe_rrhh)
    assert cobertura.status_code == 200, cobertura.text
    por_puesto = {p["puesto_id"]: p for p in cobertura.json()}

    assert por_puesto[e["puesto_critico_id"]]["sin_cobertura"] is False
    assert len(por_puesto[e["puesto_critico_id"]]["candidatos"]) == 1
    assert por_puesto[e["puesto_normal_id"]]["sin_cobertura"] is True
