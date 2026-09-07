"""T011 — integración US1: Escenarios 1 y 2 de quickstart.md (feature 002).

1. Alta con consentimiento rechazado → el job de CLV/churn no lo toca.
2. Baja con anonimización real → household_id intacto, datos anonimizados.
"""

import pytest
from src.jobs import scheduler

pytestmark = pytest.mark.asyncio


async def test_escenario_1_consentimiento_rechazado_excluye_del_calculo(
    client, escenario_pos, auth_cajero
):
    alta = await client.post(
        "/api/clientes",
        json={"nombre": "Sin Consent", "email": "e1@example.com", "consentimiento_datos": False},
        headers=auth_cajero,
    )
    assert alta.status_code == 201, alta.text
    hid = alta.json()["household_id"]

    # Forzar el job semanal (endpoint de desarrollo).
    job = await client.post("/api/_dev/jobs/clv_churn_semanal")
    assert job.status_code == 200, job.text

    detalle = (await client.get(f"/api/clientes/{hid}", headers=auth_cajero)).json()
    assert detalle["clv_score"] is None
    assert detalle["severidad_churn"] is None


async def test_escenario_2_baja_con_anonimizacion_real(
    client, escenario_pos, auth_cajero, auth_encargado
):
    alta = await client.post(
        "/api/clientes",
        json={
            "nombre": "Con Consent",
            "email": "e2@example.com",
            "telefono": "0977777777",
            "fecha_nacimiento": "1985-01-01",
            "consentimiento_datos": True,
        },
        headers=auth_cajero,
    )
    hid = alta.json()["household_id"]

    await client.delete(f"/api/clientes/{hid}", headers=auth_encargado)

    detalle = (await client.get(f"/api/clientes/{hid}", headers=auth_cajero)).json()
    assert detalle["household_id"] == hid
    assert detalle["activo"] is False
    assert detalle["nombre"] == "CLIENTE ANONIMIZADO"
    assert detalle["telefono"] is None
    assert detalle["fecha_nacimiento"] is None


async def test_los_jobs_estan_registrados():
    # 002: clv/churn + hitos. 003: propuestas de ajuste + alertas de competencia.
    assert {"clv_churn_semanal", "eventos_hito_diario"}.issubset(set(scheduler.JOBS))
    assert {"propuestas_ajuste_semanal", "alertas_competencia_semanal"}.issubset(
        set(scheduler.JOBS)
    )
