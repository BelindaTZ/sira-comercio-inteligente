"""T035 — contrato POST /api/inventario/recepciones (FR-014)."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_recepcion_crea_lote_y_pasa_orden_a_recibida(
    client, escenario_inventario, auth_reponedor, db_session
):
    e = escenario_inventario
    resp = await client.post(
        "/api/inventario/recepciones",
        json={
            "orden_id": e["orden_id"],
            "product_id": e["product_us2"],
            "tienda_id": e["tienda_id"],
            "cantidad": 100,
            "fecha_vencimiento": "2026-12-31",
            "codigo_lote_proveedor": "LOTE-XYZ",
        },
        headers=auth_reponedor,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["stock_disponible"] == 100
    assert body["lote_id"] > 0

    estado = await db_session.scalar(
        text("SELECT estado FROM ordenes_compra WHERE orden_id = :o"), {"o": e["orden_id"]}
    )
    assert estado == "recibida"

    saldo_lote = await db_session.scalar(
        text("SELECT cantidad_disponible FROM lotes WHERE lote_id = :l"), {"l": body["lote_id"]}
    )
    assert saldo_lote == 100

    mov = await db_session.scalar(
        text(
            "SELECT tipo FROM movimientos_inventario "
            "WHERE referencia_tabla = 'recepcion_mercaderia' AND referencia_id = :r"
        ),
        {"r": body["recepcion_id"]},
    )
    assert mov == "entrada"


async def test_recepcion_contra_orden_no_aprobada_falla(
    client, escenario_inventario, auth_reponedor, db_session
):
    e = escenario_inventario
    await db_session.execute(
        text("UPDATE ordenes_compra SET estado = 'pendiente' WHERE orden_id = :o"),
        {"o": e["orden_id"]},
    )
    resp = await client.post(
        "/api/inventario/recepciones",
        json={
            "orden_id": e["orden_id"],
            "product_id": e["product_us2"],
            "tienda_id": e["tienda_id"],
            "cantidad": 10,
        },
        headers=auth_reponedor,
    )
    assert resp.status_code == 422, resp.text


async def test_recepcion_exige_autenticacion(client, escenario_inventario):
    e = escenario_inventario
    resp = await client.post(
        "/api/inventario/recepciones",
        json={
            "orden_id": e["orden_id"],
            "product_id": e["product_us2"],
            "tienda_id": e["tienda_id"],
            "cantidad": 10,
        },
    )
    assert resp.status_code == 401
