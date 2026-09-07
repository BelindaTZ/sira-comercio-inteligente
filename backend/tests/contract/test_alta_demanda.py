"""T084 — contrato POST /api/inventario/verificacion-anaquel y quiebre de alta
demanda (FR-042, FR-043, Ronda 10)."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _marcar_clase_a(db_session, product_id):
    await db_session.execute(
        text("UPDATE productos SET clasificacion_abc = 'A' WHERE product_id = :p"),
        {"p": product_id},
    )
    await db_session.flush()


async def test_verificacion_anaquel_solo_clase_a(client, escenario_pos, auth_reponedor, db_session):
    e = escenario_pos
    # El producto por defecto no es clase A → 422
    resp = await client.post(
        "/api/inventario/verificacion-anaquel",
        json={
            "product_id": e["product_id"],
            "tienda_id": e["tienda_id"],
            "disponible": True,
            "empleado_id": e["encargado_id"],
        },
        headers=auth_reponedor,
    )
    assert resp.status_code == 422, resp.text

    await _marcar_clase_a(db_session, e["product_id"])
    ok = await client.post(
        "/api/inventario/verificacion-anaquel",
        json={
            "product_id": e["product_id"],
            "tienda_id": e["tienda_id"],
            "disponible": False,
            "empleado_id": e["encargado_id"],
        },
        headers=auth_reponedor,
    )
    assert ok.status_code == 201, ok.text


async def test_verificacion_anaquel_upsert_por_dia(
    client, escenario_pos, auth_reponedor, db_session
):
    e = escenario_pos
    await _marcar_clase_a(db_session, e["product_id"])
    payload = {
        "product_id": e["product_id"],
        "tienda_id": e["tienda_id"],
        "disponible": True,
        "empleado_id": e["encargado_id"],
        "fecha": "2026-09-06",
    }
    r1 = await client.post(
        "/api/inventario/verificacion-anaquel", json=payload, headers=auth_reponedor
    )
    payload["disponible"] = False
    r2 = await client.post(
        "/api/inventario/verificacion-anaquel", json=payload, headers=auth_reponedor
    )
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.json()["disponible"] is False

    filas = await db_session.scalar(
        text(
            "SELECT COUNT(*) FROM verificacion_anaquel "
            "WHERE product_id = :p AND tienda_id = :t AND fecha = '2026-09-06'"
        ),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    assert filas == 1


async def test_quiebre_de_producto_clase_a_es_alta_demanda(
    client, escenario_pos, auth_reponedor, db_session
):
    e = escenario_pos
    await _marcar_clase_a(db_session, e["product_id"])
    resp = await client.post(
        "/api/inventario/quiebres",
        json={
            "product_id": e["product_id"],
            "tienda_id": e["tienda_id"],
            "empleado_id": e["encargado_id"],
            "demanda_estimada_no_satisfecha": 12,
        },
        headers=auth_reponedor,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["es_alta_demanda"] is True


async def test_quiebre_de_producto_no_clase_a_no_es_alta_demanda(
    client, escenario_pos, auth_reponedor
):
    e = escenario_pos
    resp = await client.post(
        "/api/inventario/quiebres",
        json={
            "product_id": e["product_id"],
            "tienda_id": e["tienda_id"],
            "empleado_id": e["encargado_id"],
        },
        headers=auth_reponedor,
    )
    assert resp.status_code == 201
    assert resp.json()["es_alta_demanda"] is False
