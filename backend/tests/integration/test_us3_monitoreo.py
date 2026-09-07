"""T028 + T030 — integración US3: Escenario 5 de quickstart.md.

El job semanal compara el pronóstico contra la demanda real observada y calcula
el WAPE; marca alerta si supera `umbral_degradacion_semanal_pct`. El histórico
completo por modelo queda consultable, no sólo la última semana (FR-013).
"""

from datetime import datetime

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _ventas_semana(db_session, e, semana, unidades):
    venta_id = await db_session.scalar(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
            "VALUES (:t, :c, :f, :sem, 0, 'confirmada') RETURNING venta_id"
        ),
        {
            "t": e["tienda_id"],
            "c": e["cajero_id"],
            "f": datetime(e["anio_historial"], 6, 1),
            "sem": semana,
        },
    )
    await db_session.execute(
        text(
            "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
            "VALUES (:v, :p, :cant, 2.50)"
        ),
        {"v": venta_id, "p": e["product_id"], "cant": unidades},
    )
    await db_session.flush()


async def test_monitoreo_semanal_con_historico_y_alerta(
    client, escenario_forecasting, auth_jefe_ti, db_session
):
    e = escenario_forecasting
    anio = e["anio_historial"]
    m = (await client.post("/api/forecasting/modelos/entrenar", headers=auth_jefe_ti)).json()[
        "modelo_id"
    ]
    await client.post(f"/api/forecasting/modelos/{m}/aprobar", headers=auth_jefe_ti)

    # semana 17: demanda real cercana al pronóstico → sin alerta
    await _ventas_semana(db_session, e, 17, 11)
    r1 = await client.post(
        f"/api/forecasting/monitoreo/calcular?semana=17&anio={anio}", headers=auth_jefe_ti
    )
    assert r1.status_code == 201, r1.text
    assert r1.json()["calculado"] is True

    # semana 18: demanda real MUY lejos del pronóstico → debe superar el umbral
    await _ventas_semana(db_session, e, 18, 90)
    r2 = await client.post(
        f"/api/forecasting/monitoreo/calcular?semana=18&anio={anio}", headers=auth_jefe_ti
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["supero_umbral_alerta"] is True

    # histórico completo del modelo (no sólo la última) — FR-013
    hist = (
        await client.get(f"/api/forecasting/modelos/{m}/monitoreo", headers=auth_jefe_ti)
    ).json()
    semanas = sorted(h["semana"] for h in hist)
    assert semanas == [17, 18]

    # alertas: el modelo aparece porque su medición más reciente superó el umbral
    alertas = (await client.get("/api/forecasting/monitoreo/alertas", headers=auth_jefe_ti)).json()
    assert any(a["modelo_id"] == m and a["semana"] == 18 for a in alertas)


async def test_sin_modelo_vigente_no_calcula(client, escenario_forecasting, auth_jefe_ti):
    resp = await client.post("/api/forecasting/monitoreo/calcular", headers=auth_jefe_ti)
    assert resp.status_code == 201
    assert resp.json()["calculado"] is False
