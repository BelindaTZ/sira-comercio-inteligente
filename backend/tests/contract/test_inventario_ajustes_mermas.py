"""T036 — contrato POST /api/inventario/ajustes y /api/inventario/mermas
(FR-017, FR-018, FR-019)."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_ajuste_reconcilia_el_inventario_con_el_conteo_fisico(
    client, escenario_pos, auth_reponedor, db_session
):
    e = escenario_pos
    # escenario_pos deja inventario en 100
    resp = await client.post(
        "/api/inventario/ajustes",
        json={
            "product_id": e["product_id"],
            "tienda_id": e["tienda_id"],
            "cantidad_fisica": 93,
            "empleado_id": e["encargado_id"],
        },
        headers=auth_reponedor,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["cantidad_sistema"] == 100
    assert body["diferencia"] == -7
    assert body["stock_disponible"] == 93

    disponible = await db_session.scalar(
        text(
            "SELECT cantidad_disponible FROM inventario " "WHERE product_id = :p AND tienda_id = :t"
        ),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    assert disponible == 93


async def test_merma_queda_pendiente_y_no_descuenta_stock_hasta_validar(
    client, escenario_pos, auth_reponedor, auth_encargado, db_session
):
    e = escenario_pos
    resp = await client.post(
        "/api/inventario/mermas",
        json={
            "product_id": e["product_id"],
            "tienda_id": e["tienda_id"],
            "cantidad": 5,
            "causa": "rotura",
            "empleado_id": e["encargado_id"],
        },
        headers=auth_reponedor,
    )
    assert resp.status_code == 201, resp.text
    merma = resp.json()
    assert merma["estado_validacion"] == "pendiente"
    assert merma["valor"] == "5.00"  # 5 * costo 1.00

    antes = await db_session.scalar(
        text("SELECT cantidad_disponible FROM inventario WHERE product_id = :p AND tienda_id = :t"),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    assert antes == 100  # aún no se descontó

    val = await client.post(
        f"/api/inventario/mermas/{merma['merma_id']}/validar",
        json={"empleado_id": e["encargado_id"], "decision": "validada"},
        headers=auth_encargado,
    )
    assert val.status_code == 200, val.text
    assert val.json()["estado_validacion"] == "validada"

    despues = await db_session.scalar(
        text("SELECT cantidad_disponible FROM inventario WHERE product_id = :p AND tienda_id = :t"),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    assert despues == 95


async def test_merma_rechazada_no_altera_stock(
    client, escenario_pos, auth_reponedor, auth_encargado, db_session
):
    e = escenario_pos
    merma = (
        await client.post(
            "/api/inventario/mermas",
            json={
                "product_id": e["product_id"],
                "tienda_id": e["tienda_id"],
                "cantidad": 3,
                "causa": "robo",
                "empleado_id": e["encargado_id"],
            },
            headers=auth_reponedor,
        )
    ).json()

    val = await client.post(
        f"/api/inventario/mermas/{merma['merma_id']}/validar",
        json={"empleado_id": e["encargado_id"], "decision": "rechazada"},
        headers=auth_encargado,
    )
    assert val.status_code == 200
    disponible = await db_session.scalar(
        text("SELECT cantidad_disponible FROM inventario WHERE product_id = :p AND tienda_id = :t"),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    assert disponible == 100


async def test_reponedor_no_puede_validar_mermas(client, escenario_pos, auth_reponedor):
    e = escenario_pos
    merma = (
        await client.post(
            "/api/inventario/mermas",
            json={
                "product_id": e["product_id"],
                "tienda_id": e["tienda_id"],
                "cantidad": 1,
                "causa": "caducidad",
                "empleado_id": e["encargado_id"],
            },
            headers=auth_reponedor,
        )
    ).json()
    resp = await client.post(
        f"/api/inventario/mermas/{merma['merma_id']}/validar",
        json={"empleado_id": e["encargado_id"], "decision": "validada"},
        headers=auth_reponedor,
    )
    assert resp.status_code == 403, resp.text


async def test_listar_y_kpis_mermas(client, escenario_pos, auth_encargado):
    e = escenario_pos
    await client.post(
        "/api/inventario/mermas",
        json={
            "product_id": e["product_id"],
            "tienda_id": e["tienda_id"],
            "cantidad": 2,
            "causa": "rotura",
            "empleado_id": e["encargado_id"],
            "destino": "destruccion",
            "observaciones": "Botella quebrada en góndola",
        },
        headers=auth_encargado,
    )
    resp = await client.get(
        f"/api/inventario/mermas?tienda_id={e['tienda_id']}",
        headers=auth_encargado,
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert "product_nombre" in items[0]
    assert items[0]["causa"] in ("rotura", "caducidad", "robo", "error_humano")

    kpis_resp = await client.get(
        f"/api/inventario/mermas/kpis?tienda_id={e['tienda_id']}",
        headers=auth_encargado,
    )
    assert kpis_resp.status_code == 200
    kpis = kpis_resp.json()
    assert "merma_acumulada_mes" in kpis
    assert "causas_desglose" in kpis
