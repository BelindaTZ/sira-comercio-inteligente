"""T028 — integración US3: Escenario 4 de quickstart.md (FR-010, SC-002).

Un cliente cuyo `dias_desde_ultima_compra` supera 1.5x su ciclo pero no 3x
aparece sólo en `severidad=en_riesgo`; otro que supera 3x, sólo en `inactivo`.
La severidad es relativa al ciclo propio de cada cliente, nunca un umbral fijo.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _alta(client, auth, email) -> int:
    return (
        await client.post(
            "/api/clientes",
            json={"nombre": email, "email": email, "consentimiento_datos": True},
            headers=auth,
        )
    ).json()["household_id"]


async def _compras(db_session, e, household_id, dias_atras: list[int]) -> None:
    for d in dias_atras:
        venta_id = await db_session.scalar(
            text(
                "INSERT INTO ventas (tienda_id, cajero_id, household_id, fecha_hora, semana, "
                "total, estado) VALUES (:t, :c, :h, :f, 1, 5, 'confirmada') RETURNING venta_id"
            ),
            {
                "t": e["tienda_id"],
                "c": e["cajero_id"],
                "h": household_id,
                "f": date.today() - timedelta(days=d),
            },
        )
        await db_session.execute(
            text(
                "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
                "VALUES (:v, :p, 1, 5)"
            ),
            {"v": venta_id, "p": e["product_id"]},
        )
    await db_session.flush()


async def test_escenario_4_severidad_relativa_al_ciclo_individual(
    client, escenario_pos, auth_cajero, auth_jefe_marketing, db_session
):
    e = escenario_pos

    # A: ciclo corto (~7 días), última compra hace 20 → 20 > 1.5·7 pero < 3·7.
    a = await _alta(client, auth_cajero, "churn-a@e.com")
    await _compras(db_session, e, a, [48, 41, 34, 27, 20])

    # B: ciclo largo (~30 días), última compra también hace 20 → dentro de su
    #    patrón normal. Mismo `dias_desde_ultima_compra` que A, veredicto distinto.
    b = await _alta(client, auth_cajero, "churn-b@e.com")
    await _compras(db_session, e, b, [110, 80, 50, 20])

    # C: ciclo corto (~7 días), última compra hace 60 → 60 > 3·7 → inactivo.
    c = await _alta(client, auth_cajero, "churn-c@e.com")
    await _compras(db_session, e, c, [88, 81, 74, 67, 60])

    job = await client.post("/api/_dev/jobs/clv_churn_semanal")
    assert job.status_code == 200, job.text
    assert job.json()["clientes_con_churn"] >= 3

    en_riesgo = (
        await client.get(
            "/api/clientes/riesgo-fuga?severidad=en_riesgo", headers=auth_jefe_marketing
        )
    ).json()["items"]
    inactivos = (
        await client.get(
            "/api/clientes/riesgo-fuga?severidad=inactivo", headers=auth_jefe_marketing
        )
    ).json()["items"]

    ids_riesgo = {r["household_id"] for r in en_riesgo}
    ids_inactivo = {r["household_id"] for r in inactivos}

    assert a in ids_riesgo and a not in ids_inactivo
    assert c in ids_inactivo and c not in ids_riesgo
    # B: mismo lapso que A desde la última compra, pero dentro de su ciclo.
    assert b not in ids_riesgo and b not in ids_inactivo
