"""T079 — contrato PUT /api/inventario/stock-maximo + alerta `exceso_stock`
(FR-037, FR-038, Ronda 9)."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_put_stock_maximo_hace_upsert(client, escenario_compras, auth_jefe_ops):
    e = escenario_compras
    body = {
        "product_category": "TEST CAT",
        "tienda_id": e["tienda_id"],
        "cantidad_maxima": 500,
        "empleado_id": e["jefe_ops_id"],
    }
    r1 = await client.put("/api/inventario/stock-maximo", json=body, headers=auth_jefe_ops)
    assert r1.status_code == 200, r1.text
    assert r1.json()["cantidad_maxima"] == 500

    body["cantidad_maxima"] = 300
    r2 = await client.put("/api/inventario/stock-maximo", json=body, headers=auth_jefe_ops)
    assert r2.status_code == 200
    assert r2.json()["id"] == r1.json()["id"]  # misma fila (upsert)
    assert r2.json()["cantidad_maxima"] == 300


async def test_reponedor_no_puede_definir_stock_maximo(client, escenario_compras, auth_reponedor):
    e = escenario_compras
    resp = await client.put(
        "/api/inventario/stock-maximo",
        json={
            "product_category": "TEST CAT",
            "tienda_id": e["tienda_id"],
            "cantidad_maxima": 100,
            "empleado_id": e["reponedor_id"],
        },
        headers=auth_reponedor,
    )
    assert resp.status_code == 403, resp.text


async def test_recepcion_por_encima_del_maximo_genera_alerta_exceso(
    client, escenario_compras, auth_jefe_ops, auth_reponedor, db_session
):
    e = escenario_compras
    # Máximo bajo para la categoría del product_us2 ('CAT US2')
    await client.put(
        "/api/inventario/stock-maximo",
        json={
            "product_category": "CAT US2",
            "tienda_id": e["tienda_id"],
            "cantidad_maxima": 50,
            "empleado_id": e["jefe_ops_id"],
        },
        headers=auth_jefe_ops,
    )
    # Recepción de 100 → deja el stock (100) por encima del máximo (50)
    rec = await client.post(
        "/api/inventario/recepciones",
        json={
            "orden_id": e["orden_id"],
            "product_id": e["product_us2"],
            "tienda_id": e["tienda_id"],
            "cantidad": 100,
        },
        headers=auth_reponedor,
    )
    assert rec.status_code == 201, rec.text

    alerta = await db_session.scalar(
        text(
            "SELECT COUNT(*) FROM alertas_inventario "
            "WHERE product_id = :p AND tienda_id = :t AND tipo = 'exceso_stock' "
            "AND estado = 'pendiente'"
        ),
        {"p": e["product_us2"], "t": e["tienda_id"]},
    )
    assert alerta == 1
