"""Contrato — GET /api/inventario/lotes y /alertas aceptan `search` por nombre o id.

El buscador de la pantalla de Gestión (feature 013) manda texto libre: si es un
número se filtra por `product_id`; si no, por `nombre` / `product_type` / `marca`
del producto (ILIKE). Antes sólo aceptaba `product_id` numérico.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _nombrar_producto(db_session, product_id: int, nombre: str, marca: str) -> None:
    await db_session.execute(
        text("UPDATE productos SET nombre = :n, marca = :m WHERE product_id = :p"),
        {"n": nombre, "m": marca, "p": product_id},
    )
    await db_session.flush()


async def test_lotes_search_por_nombre(client, escenario_pos, auth_encargado, db_session):
    e = escenario_pos
    await _nombrar_producto(db_session, e["product_id"], "Yogurt Griego Natural", "Del Sur")

    ok = await client.get(
        "/api/inventario/lotes",
        params={"tienda_id": e["tienda_id"], "search": "yogurt"},
        headers=auth_encargado,
    )
    assert ok.status_code == 200, ok.text
    cuerpo = ok.json()
    assert cuerpo["total"] >= 1
    assert all(x["product_id"] == e["product_id"] for x in cuerpo["items"])
    assert cuerpo["items"][0]["producto_nombre"] == "Yogurt Griego Natural"

    vacio = await client.get(
        "/api/inventario/lotes",
        params={"tienda_id": e["tienda_id"], "search": "no-existe-zzz"},
        headers=auth_encargado,
    )
    assert vacio.status_code == 200
    assert vacio.json()["total"] == 0


async def test_lotes_search_numerico_es_product_id(client, escenario_pos, auth_encargado):
    e = escenario_pos
    r = await client.get(
        "/api/inventario/lotes",
        params={"tienda_id": e["tienda_id"], "search": str(e["product_id"])},
        headers=auth_encargado,
    )
    assert r.status_code == 200, r.text
    assert r.json()["total"] >= 1
    assert all(x["product_id"] == e["product_id"] for x in r.json()["items"])


async def test_alertas_search_por_nombre(client, escenario_pos, auth_encargado, db_session):
    e = escenario_pos
    await _nombrar_producto(db_session, e["product_id"], "Aceite Oliva Extra", "Valle")
    await db_session.execute(
        text(
            "INSERT INTO alertas_inventario (tipo, product_id, tienda_id, estado) "
            "VALUES ('reposicion', :p, :t, 'pendiente')"
        ),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    await db_session.flush()

    r = await client.get(
        "/api/inventario/alertas",
        params={"tienda_id": e["tienda_id"], "search": "aceite"},
        headers=auth_encargado,
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["total"] >= 1
    assert cuerpo["items"][0]["producto_nombre"] == "Aceite Oliva Extra"
