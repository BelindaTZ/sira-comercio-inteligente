"""T027 — contrato GET /api/clientes/riesgo-fuga?severidad= (FR-011, SC-005).

El filtro por severidad es exacto y cada fila trae `ciclo_compra_dias` y
`dias_desde_ultima_compra` ya calculados — el Jefe de Marketing no los deriva.
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


async def test_riesgo_fuga_filtra_por_severidad_y_precalcula(
    client, escenario_pos, auth_jefe_marketing, auth_cajero, db_session
):
    e = escenario_pos
    riesgo = await _alta(client, auth_cajero, "en-riesgo@e.com")
    inactivo = await _alta(client, auth_cajero, "inactivo@e.com")
    sano = await _alta(client, auth_cajero, "sano@e.com")

    # ciclo ~10 días en los tres; cambia sólo cuánto hace de la última compra.
    await _compras(db_session, e, riesgo, [60, 50, 40, 30, 20])  # última hace 20 → >1.5x, <3x
    await _compras(db_session, e, inactivo, [110, 100, 90, 80, 70])  # última hace 70 → >3x
    await _compras(db_session, e, sano, [40, 30, 20, 10, 3])  # dentro de su ciclo

    job = await client.post("/api/_dev/jobs/clv_churn_semanal")
    assert job.status_code == 200, job.text

    er = (
        await client.get(
            "/api/clientes/riesgo-fuga?severidad=en_riesgo", headers=auth_jefe_marketing
        )
    ).json()
    ids_er = {r["household_id"] for r in er["items"]}
    assert riesgo in ids_er
    assert inactivo not in ids_er and sano not in ids_er

    ina = (
        await client.get(
            "/api/clientes/riesgo-fuga?severidad=inactivo", headers=auth_jefe_marketing
        )
    ).json()
    ids_ina = {r["household_id"] for r in ina["items"]}
    assert inactivo in ids_ina
    assert riesgo not in ids_ina and sano not in ids_ina

    fila = next(r for r in er["items"] if r["household_id"] == riesgo)
    assert fila["ciclo_compra_dias"] is not None
    assert fila["dias_desde_ultima_compra"] is not None
    assert fila["severidad"] == "en_riesgo"


async def test_sin_severidad_devuelve_todos_los_que_tienen_riesgo(
    client, escenario_pos, auth_jefe_marketing, auth_cajero, db_session
):
    e = escenario_pos
    riesgo = await _alta(client, auth_cajero, "r2@e.com")
    inactivo = await _alta(client, auth_cajero, "i2@e.com")
    await _compras(db_session, e, riesgo, [60, 50, 40, 30, 20])
    await _compras(db_session, e, inactivo, [110, 100, 90, 80, 70])

    await client.post("/api/_dev/jobs/clv_churn_semanal")
    todos = (await client.get("/api/clientes/riesgo-fuga", headers=auth_jefe_marketing)).json()
    ids = {r["household_id"] for r in todos["items"]}
    assert {riesgo, inactivo} <= ids
    assert all(r["severidad"] in ("en_riesgo", "inactivo") for r in todos["items"])


async def test_cajero_no_puede_ver_riesgo_de_fuga(client, escenario_pos, auth_cajero):
    resp = await client.get("/api/clientes/riesgo-fuga", headers=auth_cajero)
    assert resp.status_code == 403, resp.text
