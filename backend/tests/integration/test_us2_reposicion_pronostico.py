"""T021 — integración US2: Escenarios 3 y 4 de quickstart.md.

3: con pronóstico vigente, la alerta de reposición y la sugerencia de compra
   usan el modelo (`origen_calculo = 'modelo_pronostico'`).
4: sin pronóstico (cold start), ambos siguen calculándose con la rotación
   reciente de 001 (`origen_calculo = 'rotacion_reciente'`), nunca sin valor.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _aprobar_modelo(client, auth):
    m = (await client.post("/api/forecasting/modelos/entrenar", headers=auth)).json()["modelo_id"]
    await client.post(f"/api/forecasting/modelos/{m}/aprobar", headers=auth)
    return m


async def test_escenario_3_y_4_origen_calculo(
    client, escenario_forecasting, auth_jefe_ti, auth_encargado, db_session
):
    e = escenario_forecasting
    await _aprobar_modelo(client, auth_jefe_ti)

    # dejar el producto principal con stock bajo → la alerta se disparará
    await db_session.execute(
        text(
            "UPDATE inventario SET cantidad_disponible = 2 "
            "WHERE product_id = :p AND tienda_id = :t"
        ),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    # producto cold start: inventario propio + ventas RECIENTES (para que la
    # rotación reciente de 001 sí produzca un punto > 0)
    await db_session.execute(
        text(
            "INSERT INTO inventario (product_id, tienda_id, cantidad_disponible) "
            "VALUES (:p, :t, 1)"
        ),
        {"p": e["product_cold"], "t": e["tienda_id"]},
    )
    venta_id = await db_session.scalar(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
            "VALUES (:t, :c, :f, 1, 0, 'confirmada') RETURNING venta_id"
        ),
        {"t": e["tienda_id"], "c": e["cajero_id"], "f": datetime.now(UTC).replace(tzinfo=None)},
    )
    await db_session.execute(
        text(
            "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
            "VALUES (:v, :p, 20, 3.00)"
        ),
        {"v": venta_id, "p": e["product_cold"]},
    )
    await db_session.flush()

    job = await client.post(
        f"/api/inventario/jobs/reposicion?tienda_id={e['tienda_id']}", headers=auth_encargado
    )
    assert job.status_code == 200, job.text
    generadas = {g["product_id"]: g["origen_calculo"] for g in job.json()["alertas_generadas"]}
    assert generadas.get(e["product_id"]) == "modelo_pronostico"
    assert generadas.get(e["product_cold"]) == "rotacion_reciente"

    # la alerta persistida también trae el origen
    alertas = (
        await client.get(
            f"/api/inventario/alertas?tipo=reposicion&tienda_id={e['tienda_id']}",
            headers=auth_encargado,
        )
    ).json()["items"]
    origen_por_prod = {a["product_id"]: a["origen_calculo"] for a in alertas}
    assert origen_por_prod[e["product_id"]] == "modelo_pronostico"
    assert origen_por_prod[e["product_cold"]] == "rotacion_reciente"

    # sugerencia de compra: mismo origen por producto
    sugs = (
        await client.get(
            f"/api/compras/sugerencias?tienda_id={e['tienda_id']}", headers=auth_encargado
        )
    ).json()
    origen_sug = {s["product_id"]: s["origen_calculo"] for s in sugs}
    assert origen_sug.get(e["product_id"]) == "modelo_pronostico"
    assert origen_sug.get(e["product_cold"]) == "rotacion_reciente"
