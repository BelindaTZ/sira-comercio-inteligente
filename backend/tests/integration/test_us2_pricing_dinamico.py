"""T021 — integración US2: Escenarios 1 y 2 de quickstart.md.

Escenario 1: margen objetivo efectivo ancla ≠ nicho de la misma categoría.
Escenario 2: la propuesta de ajuste nunca se publica sin aprobación explícita.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_escenario_1_margen_efectivo_diferenciado(
    client, escenario_pricing, auth_pricing_jc, db_session
):
    e = escenario_pricing
    await client.patch(
        "/api/pricing/margenes/TEST CAT",
        json={"margen_objetivo_pct": "20"},
        headers=auth_pricing_jc,
    )
    ancla_id = await db_session.scalar(text("SELECT COALESCE(MAX(product_id),0)+1 FROM productos"))
    await db_session.execute(
        text(
            "INSERT INTO productos (product_id, product_category, product_type, costo, "
            "precio_base, es_ancla) VALUES (:p, 'TEST CAT', 'ANCLA', 1.00, 2.50, true)"
        ),
        {"p": ancla_id},
    )
    await db_session.flush()

    ancla = (
        await client.get(
            f"/api/pricing/productos/{ancla_id}/margen-efectivo", headers=auth_pricing_jc
        )
    ).json()
    nicho = (
        await client.get(
            f"/api/pricing/productos/{e['product_id']}/margen-efectivo", headers=auth_pricing_jc
        )
    ).json()
    assert float(ancla["margen_objetivo_efectivo"]) == 15.0
    assert float(nicho["margen_objetivo_efectivo"]) == 23.0


async def test_escenario_2_propuesta_no_se_publica_sin_aprobacion(
    client, escenario_pricing, auth_pricing_jc, db_session
):
    e = escenario_pricing
    await client.patch(
        "/api/pricing/margenes/TEST CAT",
        json={"margen_objetivo_pct": "20", "factor_sensibilidad": "0.3"},
        headers=auth_pricing_jc,
    )
    venta_id = await db_session.scalar(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
            "VALUES (:t, :c, :f, 1, 25, 'confirmada') RETURNING venta_id"
        ),
        {"t": e["tienda_id"], "c": e["cajero_id"], "f": date.today() - timedelta(days=2)},
    )
    await db_session.execute(
        text(
            "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
            "VALUES (:v, :p, 10, 2.50)"
        ),
        {"v": venta_id, "p": e["product_id"]},
    )
    await db_session.flush()

    assert (await client.post("/api/_dev/jobs/propuestas_ajuste_semanal")).status_code == 200
    props = (
        await client.get("/api/pricing/propuestas?estado=pendiente", headers=auth_pricing_jc)
    ).json()
    assert props["total"] >= 1
    propuesta = props["items"][0]

    # el precio de catálogo sigue igual mientras la propuesta esté pendiente
    precio = await db_session.scalar(
        text("SELECT precio_base FROM productos WHERE product_id = :p"), {"p": e["product_id"]}
    )
    assert float(precio) == 2.50

    await client.post(
        f"/api/pricing/propuestas/{propuesta['propuesta_id']}/aprobar", headers=auth_pricing_jc
    )
    precio = await db_session.scalar(
        text("SELECT precio_base FROM productos WHERE product_id = :p"), {"p": e["product_id"]}
    )
    assert float(precio) == float(propuesta["precio_propuesto"])
