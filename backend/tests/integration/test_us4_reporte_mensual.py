"""T040 — integración US4: Escenario 7 de quickstart.md (FR-013).

El reporte mensual de margen es `GET /api/pricing/reportes/margen` invocado con el
rango del mes: cada categoría con ventas muestra su margen real acumulado junto a
su margen objetivo vigente, sin cálculo manual.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_reporte_mensual_margen_real_vs_objetivo(
    client, escenario_pricing, auth_pricing_jc, db_session
):
    e = escenario_pricing
    await client.patch(
        "/api/pricing/margenes/TEST CAT",
        json={"margen_objetivo_pct": "30"},
        headers=auth_pricing_jc,
    )

    # dos ventas confirmadas hoy: ingreso 2.50/ud, costo 1.00/ud → margen 60%
    for dias in (0, 0):
        venta_id = await db_session.scalar(
            text(
                "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
                "VALUES (:t, :c, :f, 1, 25, 'confirmada') RETURNING venta_id"
            ),
            {"t": e["tienda_id"], "c": e["cajero_id"], "f": date.today() - timedelta(days=dias)},
        )
        await db_session.execute(
            text(
                "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
                "VALUES (:v, :p, 5, 2.50)"
            ),
            {"v": venta_id, "p": e["product_id"]},
        )
    await db_session.flush()

    primero = date.today().replace(day=1)
    reporte = (
        await client.get(
            "/api/pricing/reportes/margen",
            params={
                "fecha_desde": primero.isoformat(),
                "fecha_hasta": (date.today() + timedelta(days=1)).isoformat(),
                "product_category": "TEST CAT",
            },
            headers=auth_pricing_jc,
        )
    ).json()
    fila = next(f for f in reporte["filas"] if f["product_category"] == "TEST CAT")
    assert fila["margen_objetivo_pct"] == "30.00"
    assert float(fila["margen_real_pct"]) == 60.0
    assert fila["unidades_vendidas"] == 10
