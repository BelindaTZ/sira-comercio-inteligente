"""T008/T009 — contrato de puestos críticos y acciones de retención (feature 011,
`contracts/recursos-humanos.md`, FR-001/FR-002).
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_marcar_critico_y_registrar_retencion(client, escenario_rrhh, auth_jefe_rrhh):
    e = escenario_rrhh

    critico = await client.patch(
        f"/api/rrhh/puestos/{e['puesto_normal_id']}/critico",
        json={"es_critico": True},
        headers=auth_jefe_rrhh,
    )
    assert critico.status_code == 200, critico.text
    assert critico.json()["es_critico"] is True

    accion = await client.post(
        "/api/rrhh/acciones-retencion",
        json={
            "empleado_id": e["cajero_a1"],
            "fecha": "2026-03-01",
            "descripcion": "Ajuste salarial + plan de carrera",
        },
        headers=auth_jefe_rrhh,
    )
    assert accion.status_code == 201, accion.text
    assert accion.json()["empleado_id"] == e["cajero_a1"]

    listado = await client.get(
        f"/api/rrhh/empleados/{e['cajero_a1']}/acciones-retencion", headers=auth_jefe_rrhh
    )
    assert listado.status_code == 200
    assert len(listado.json()) == 1
    assert listado.json()[0]["descripcion"].startswith("Ajuste salarial")


async def test_retencion_en_puesto_no_critico_se_permite(client, escenario_rrhh, auth_jefe_rrhh):
    """Edge Case / FR-002: la retención puede aplicarse a cualquier empleado."""
    e = escenario_rrhh  # puesto_normal_id NO se marca crítico en este test

    accion = await client.post(
        "/api/rrhh/acciones-retencion",
        json={
            "empleado_id": e["cajero_a2"],
            "fecha": "2026-04-15",
            "descripcion": "Bono de permanencia",
        },
        headers=auth_jefe_rrhh,
    )
    assert accion.status_code == 201, accion.text


async def test_encargado_no_marca_puestos_criticos(client, escenario_rrhh, auth_encargado_rrhh):
    e = escenario_rrhh
    resp = await client.patch(
        f"/api/rrhh/puestos/{e['puesto_normal_id']}/critico",
        json={"es_critico": True},
        headers=auth_encargado_rrhh,
    )
    assert resp.status_code == 403
