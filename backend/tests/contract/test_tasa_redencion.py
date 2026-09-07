"""T033 — contrato GET /api/clientes/cupones/tasa-redencion (FR-014).

`{tipo_evento, enviados, redimidos, tasa}` agrupado por tipo de evento de hito;
`tasa = redimidos / enviados`. Sólo Jefe_Marketing (el Cajero redime en caja
pero no ve el reporte).
"""

from datetime import date

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _cliente_cumple_hoy(db_session, email) -> int:
    hoy = date.today()
    return await db_session.scalar(
        text(
            "INSERT INTO clientes (nombre, email, fecha_nacimiento, fecha_registro, "
            "consentimiento_datos, activo) VALUES (:n, :e, :fn, DATE '2020-02-15', true, true) "
            "RETURNING household_id"
        ),
        {"n": email, "e": email, "fn": date(1990, hoy.month, hoy.day)},
    )


async def _producto_ancla(db_session) -> int:
    pid = await db_session.scalar(text("SELECT COALESCE(MAX(product_id), 0) + 1 FROM productos"))
    await db_session.execute(
        text(
            "INSERT INTO productos (product_id, product_category, product_type, costo, "
            "precio_base, es_ancla, activo) VALUES (:p, 'C', 'T', 2.00, 10.00, true, true)"
        ),
        {"p": pid},
    )
    return pid


async def test_tasa_redencion_agrupa_por_tipo_evento(
    client, escenario_pos, auth_jefe_marketing, auth_cajero, db_session
):
    await _producto_ancla(db_session)
    h1 = await _cliente_cumple_hoy(db_session, "cumple-1@e.com")
    h2 = await _cliente_cumple_hoy(db_session, "cumple-2@e.com")
    await db_session.flush()

    job = await client.post("/api/_dev/jobs/eventos_hito_diario")
    assert job.status_code == 200, job.text
    assert job.json()["eventos_generados"] >= 2

    # h1 redime su cupón, h2 no.
    upc = (await client.get(f"/api/clientes/{h1}/eventos", headers=auth_jefe_marketing)).json()[0][
        "cupon_enviado"
    ]
    campaign_id = await db_session.scalar(
        text("SELECT campaign_id FROM campanas WHERE categoria_sira = 'hito' LIMIT 1")
    )
    red = await client.post(
        f"/api/clientes/cupones/{upc}/redimir",
        json={"household_id": h1, "campaign_id": campaign_id},
        headers=auth_cajero,
    )
    assert red.status_code == 201, red.text

    resp = await client.get(
        "/api/clientes/cupones/tasa-redencion?tipo_evento=cumpleanos", headers=auth_jefe_marketing
    )
    assert resp.status_code == 200, resp.text
    fila = next(f for f in resp.json() if f["tipo_evento"] == "cumpleanos")
    assert fila["enviados"] >= 2
    assert fila["redimidos"] >= 1
    assert fila["tasa"] == round(fila["redimidos"] / fila["enviados"], 4)
    _ = h2


async def test_cajero_no_ve_el_reporte_de_tasa_redencion(client, escenario_pos, auth_cajero):
    resp = await client.get("/api/clientes/cupones/tasa-redencion", headers=auth_cajero)
    assert resp.status_code == 403, resp.text
