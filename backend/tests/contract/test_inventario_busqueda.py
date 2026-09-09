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


async def test_autocompletado_productos_por_nombre_e_id(
    client, escenario_pos, auth_encargado, db_session
):
    e = escenario_pos
    await _nombrar_producto(db_session, e["product_id"], "Leche Entera 1L", "Del Campo")

    por_nombre = await client.get(
        "/api/inventario/productos", params={"q": "leche"}, headers=auth_encargado
    )
    assert por_nombre.status_code == 200, por_nombre.text
    ids = {p["product_id"] for p in por_nombre.json()}
    assert e["product_id"] in ids

    por_id = await client.get(
        "/api/inventario/productos",
        params={"q": str(e["product_id"])},
        headers=auth_encargado,
    )
    assert por_id.status_code == 200
    assert [p["product_id"] for p in por_id.json()] == [e["product_id"]]


async def test_stock_por_sku_con_ubicacion_y_estado(
    client, escenario_pos, auth_encargado, db_session
):
    e = escenario_pos
    await _nombrar_producto(db_session, e["product_id"], "Yogurt Griego", "Del Sur")
    await db_session.execute(
        text(
            "INSERT INTO inventario (product_id, tienda_id, cantidad_disponible, cantidad_minima) "
            "VALUES (:p, :t, 5, 30) "
            "ON CONFLICT (product_id, tienda_id) DO UPDATE "
            "SET cantidad_disponible = 5, cantidad_minima = 30"
        ),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    await db_session.flush()

    # ubicar el SKU en sala
    ubic = await client.put(
        "/api/inventario/ubicacion",
        json={
            "product_id": e["product_id"],
            "tienda_id": e["tienda_id"],
            "pasillo": "Pasillo 04",
            "gondola": "G-01",
            "empleado_id": e["encargado_id"],
        },
        headers=auth_encargado,
    )
    assert ubic.status_code == 200, ubic.text

    r = await client.get(
        "/api/inventario/stock",
        params={"tienda_id": e["tienda_id"], "search": "yogurt"},
        headers=auth_encargado,
    )
    assert r.status_code == 200, r.text
    fila = next(x for x in r.json()["items"] if x["product_id"] == e["product_id"])
    assert fila["pasillo"] == "Pasillo 04"
    assert fila["gondola"] == "G-01"
    assert fila["estado"] == "quiebre"  # 5 <= 30
    assert fila["cantidad_minima"] == 30

    solo_quiebre = await client.get(
        "/api/inventario/stock",
        params={"tienda_id": e["tienda_id"], "estado": "quiebre"},
        headers=auth_encargado,
    )
    assert all(x["estado"] == "quiebre" for x in solo_quiebre.json()["items"])


async def test_resumen_stock_kpis(client, escenario_pos, auth_encargado, db_session):
    e = escenario_pos
    await db_session.execute(
        text(
            "INSERT INTO inventario (product_id, tienda_id, cantidad_disponible, cantidad_minima) "
            "VALUES (:p, :t, 5, 30) "
            "ON CONFLICT (product_id, tienda_id) DO UPDATE "
            "SET cantidad_disponible = 5, cantidad_minima = 30"
        ),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    await db_session.flush()

    r = await client.get(
        "/api/inventario/stock/resumen",
        params={"tienda_id": e["tienda_id"]},
        headers=auth_encargado,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert set(d) >= {
        "skus",
        "quiebre",
        "vencido",
        "por_vencer",
        "sobre_stock",
        "normal",
        "unidades_transito",
        "tasa_merma_pct",
    }
    assert d["quiebre"] >= 1


async def test_solicitar_reposicion_deja_alerta_y_es_idempotente(
    client, escenario_pos, auth_encargado, db_session
):
    e = escenario_pos
    body = {
        "product_id": e["product_id"],
        "tienda_id": e["tienda_id"],
        "empleado_id": e["encargado_id"],
    }
    r1 = await client.post(
        "/api/inventario/solicitudes-reposicion", json=body, headers=auth_encargado
    )
    assert r1.status_code == 201, r1.text
    assert r1.json()["ya_existia"] is False
    assert r1.json()["alerta_id"]

    r2 = await client.post(
        "/api/inventario/solicitudes-reposicion", json=body, headers=auth_encargado
    )
    assert r2.status_code == 201
    assert r2.json()["ya_existia"] is True
    assert r2.json()["alerta_id"] == r1.json()["alerta_id"]

    pendientes = await db_session.scalar(
        text(
            "SELECT count(*) FROM alertas_inventario WHERE tipo = 'reposicion' "
            "AND product_id = :p AND tienda_id = :t AND estado = 'pendiente'"
        ),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    assert pendientes == 1


async def test_categorias_del_catalogo(client, escenario_pos, auth_jefe_comercial):
    r = await client.get("/api/catalogo/categorias", headers=auth_jefe_comercial)
    assert r.status_code == 200, r.text
    cats = r.json()
    assert isinstance(cats, list)
    assert "TEST CAT" in cats  # la categoría del producto de escenario_pos
    assert cats == sorted(cats)


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
