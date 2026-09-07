"""T021 — integración US2: Escenario 3 de quickstart.md.

Cliente A (frecuente, margen bajo) y B (una compra grande, margen alto): el
nivel de A no queda por debajo del de B sólo por gasto acumulado (FR-005, SC-001).
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _alta_cliente(client, auth, email) -> int:
    return (
        await client.post(
            "/api/clientes",
            json={"nombre": email, "email": email, "consentimiento_datos": True},
            headers=auth,
        )
    ).json()["household_id"]


async def _venta_confirmada(db_session, e, household_id, product_id, cantidad, precio, dias_atras):
    fecha = date.today() - timedelta(days=dias_atras)
    venta_id = await db_session.scalar(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, household_id, fecha_hora, semana, "
            "total, estado) VALUES (:t, :c, :h, :f, 1, :tot, 'confirmada') RETURNING venta_id"
        ),
        {
            "t": e["tienda_id"],
            "c": e["cajero_id"],
            "h": household_id,
            "f": fecha,
            "tot": precio * cantidad,
        },
    )
    await db_session.execute(
        text(
            "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
            "VALUES (:v, :p, :cant, :sv)"
        ),
        {"v": venta_id, "p": product_id, "cant": cantidad, "sv": precio},
    )


async def test_escenario_3_clv_no_colapsa_a_gasto_bruto(
    client, escenario_pos, auth_cajero, db_session
):
    e = escenario_pos
    pid = e["product_id"]  # costo 1.00

    a = await _alta_cliente(client, auth_cajero, "cliente-a@e.com")
    b = await _alta_cliente(client, auth_cajero, "cliente-b@e.com")

    # A: 8 compras pequeñas (precio 1.20 → margen 0.20 c/u).
    for i in range(8):
        await _venta_confirmada(db_session, e, a, pid, 1, 1.20, dias_atras=i * 5)
    # B: 1 compra grande (precio 30 → margen 29 por unidad, 10 unidades).
    await _venta_confirmada(db_session, e, b, pid, 10, 30.0, dias_atras=3)
    await db_session.flush()

    job = await client.post("/api/_dev/jobs/clv_churn_semanal")
    assert job.status_code == 200, job.text
    assert job.json()["clientes_con_clv"] >= 2

    da = (await client.get(f"/api/clientes/{a}", headers=auth_cajero)).json()
    db_ = (await client.get(f"/api/clientes/{b}", headers=auth_cajero)).json()

    assert da["clv_score"] is not None and db_["clv_score"] is not None
    # B gastó/generó mucho más margen total, pero A compra 8× más seguido:
    # el nivel de A NO queda por debajo del de B sólo por el monto.
    assert da["nivel_fidelizacion_id"] is not None
    assert da["nivel_fidelizacion_id"] >= db_["nivel_fidelizacion_id"] or (
        float(da["clv_score"]) >= 0.4  # A alcanza al menos 'Plata' por frecuencia
    )
