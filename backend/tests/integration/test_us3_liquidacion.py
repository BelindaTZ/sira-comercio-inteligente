"""T030 + T031 — integración US3: Escenarios 4 y 5 de quickstart.md.

Producto de baja rotación → clasificado C → candidato a liquidación en la tienda
donde rota poco → el Encargado lo ejecuta. Un producto con ajuste de precio
pendiente en 003 no se ofrece como candidato (FR-013).
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_clasificacion_c_y_candidato_ejecutable(
    client, escenario_promociones, auth_ops, auth_encargado
):
    e = escenario_promociones

    abc = await client.post("/api/promociones/clasificacion-abc/calcular", headers=auth_ops)
    assert abc.status_code == 201, abc.text
    assert abc.json()["productos_reclasificados"] >= 1

    cambios = (await client.get("/api/promociones/clasificacion-abc", headers=auth_ops)).json()
    cambio_c = next(c for c in cambios if c["product_id"] == e["product_c"])
    assert cambio_c["clasificacion_nueva"] == "C"

    # umbral de liquidación: 1 unidad/semana (default) — el producto C rota 0.25/sem
    reglas = (await client.get("/api/promociones/liquidacion/reglas", headers=auth_ops)).json()
    assert float(reglas["rotacion_minima_liquidacion_semanal"]) > 0

    cand = await client.post("/api/promociones/liquidacion/candidatos/calcular", headers=auth_ops)
    assert cand.status_code == 201, cand.text
    assert cand.json()["candidatos_generados"] >= 1

    lista = (
        await client.get(
            f"/api/promociones/liquidacion/candidatos?tienda_id={e['tienda_id']}", headers=auth_ops
        )
    ).json()
    fila = next(c for c in lista if c["product_id"] == e["product_c"])
    assert fila["estado"] == "candidato"

    ok = await client.post(
        f"/api/promociones/liquidacion/candidatos/{fila['candidato_id']}/ejecutar",
        headers=auth_encargado,
    )
    assert ok.status_code == 200 and ok.json()["estado"] == "ejecutado"
    assert ok.json()["ejecutado_por"] == e["encargado_id"]

    otra = await client.post(
        f"/api/promociones/liquidacion/candidatos/{fila['candidato_id']}/ejecutar",
        headers=auth_encargado,
    )
    assert otra.status_code == 409, otra.text


async def test_producto_con_precio_pendiente_no_es_candidato(
    client, escenario_promociones, auth_ops, db_session
):
    e = escenario_promociones
    await client.post("/api/promociones/clasificacion-abc/calcular", headers=auth_ops)

    # propuesta de ajuste de precio pendiente para el producto C (feature 003)
    await db_session.execute(
        text(
            "INSERT INTO propuesta_ajuste_precio "
            "(product_id, precio_actual, precio_propuesto, margen_esperado_pct, estado) "
            "VALUES (:p, 3.00, 2.70, 10.0, 'pendiente')"
        ),
        {"p": e["product_c"]},
    )
    await db_session.flush()

    await client.post("/api/promociones/liquidacion/candidatos/calcular", headers=auth_ops)
    lista = (
        await client.get(
            f"/api/promociones/liquidacion/candidatos?tienda_id={e['tienda_id']}", headers=auth_ops
        )
    ).json()
    assert all(c["product_id"] != e["product_c"] for c in lista)


async def test_patch_regla_liquidacion(client, escenario_promociones, auth_ops):
    resp = await client.patch(
        "/api/promociones/liquidacion/reglas",
        json={"rotacion_minima_liquidacion_semanal": "2.5", "descuento_liquidacion_pct": "30"},
        headers=auth_ops,
    )
    assert resp.status_code == 200, resp.text
    assert float(resp.json()["rotacion_minima_liquidacion_semanal"]) == 2.5
    assert float(resp.json()["descuento_liquidacion_pct"]) == 30
