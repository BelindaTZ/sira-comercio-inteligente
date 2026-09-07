"""T020 — contrato de propuestas de ajuste de precio (FR-006, SC-002).

`aprobar` actualiza `productos.precio_base` + `historial_precios`; `rechazar` no
cambia nada; una propuesta ya resuelta responde 409.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _venta_confirmada(db_session, e, cantidad, precio, sales_value):
    venta_id = await db_session.scalar(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
            "VALUES (:t, :c, :f, 1, :tot, 'confirmada') RETURNING venta_id"
        ),
        {
            "t": e["tienda_id"],
            "c": e["cajero_id"],
            "f": date.today() - timedelta(days=3),
            "tot": precio * cantidad,
        },
    )
    await db_session.execute(
        text(
            "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
            "VALUES (:v, :p, :cant, :sv)"
        ),
        {"v": venta_id, "p": e["product_id"], "cant": cantidad, "sv": sales_value},
    )


async def _generar_propuesta(client, db_session, e, auth):
    # categoría con regla de ajuste + ventas cuyo margen real se desvía del objetivo.
    await client.patch(
        "/api/pricing/margenes/TEST CAT",
        json={"margen_objetivo_pct": "20", "factor_sensibilidad": "0.3"},
        headers=auth,
    )
    await _venta_confirmada(db_session, e, cantidad=10, precio=2.50, sales_value=2.50)
    await db_session.flush()
    job = await client.post("/api/_dev/jobs/propuestas_ajuste_semanal")
    assert job.status_code == 200, job.text
    props = (await client.get("/api/pricing/propuestas?estado=pendiente", headers=auth)).json()
    assert props["total"] >= 1
    return props["items"][0]


async def test_aprobar_publica_precio_y_escribe_historial(
    client, escenario_pricing, auth_pricing_jc, db_session
):
    e = escenario_pricing
    propuesta = await _generar_propuesta(client, db_session, e, auth_pricing_jc)

    # antes de aprobar: el precio de catálogo NO cambió (SC-002)
    antes = await db_session.scalar(
        text("SELECT precio_base FROM productos WHERE product_id = :p"), {"p": e["product_id"]}
    )
    assert float(antes) == 2.50

    ok = await client.post(
        f"/api/pricing/propuestas/{propuesta['propuesta_id']}/aprobar", headers=auth_pricing_jc
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["estado"] == "aprobada"

    despues = await db_session.scalar(
        text("SELECT precio_base FROM productos WHERE product_id = :p"), {"p": e["product_id"]}
    )
    assert float(despues) == float(propuesta["precio_propuesto"])
    vigente = await db_session.scalar(
        text(
            "SELECT COUNT(*) FROM historial_precios WHERE product_id = :p "
            "AND fecha_fin IS NULL AND fecha_inicio = CURRENT_DATE"
        ),
        {"p": e["product_id"]},
    )
    assert vigente == 1

    # segunda aprobación → 409
    otra = await client.post(
        f"/api/pricing/propuestas/{propuesta['propuesta_id']}/aprobar", headers=auth_pricing_jc
    )
    assert otra.status_code == 409, otra.text


async def test_rechazar_no_cambia_nada(client, escenario_pricing, auth_pricing_jc, db_session):
    e = escenario_pricing
    propuesta = await _generar_propuesta(client, db_session, e, auth_pricing_jc)

    resp = await client.post(
        f"/api/pricing/propuestas/{propuesta['propuesta_id']}/rechazar",
        json={"motivo": "temporada alta"},
        headers=auth_pricing_jc,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "rechazada"

    precio = await db_session.scalar(
        text("SELECT precio_base FROM productos WHERE product_id = :p"), {"p": e["product_id"]}
    )
    assert float(precio) == 2.50
