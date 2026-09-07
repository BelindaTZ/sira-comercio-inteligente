"""T037 — integración US2: Escenario 6 de quickstart.md (recepción + rotación FEFO).

1. Recepción de dos lotes del mismo producto con distinta fecha de vencimiento.
2. Venta de una cantidad que sólo alcanza el primer lote.
3. El descuento toma primero el lote que vence antes; `GET /inventario/lotes`
   lo prioriza visualmente (orden por fecha de vencimiento).
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _orden_aprobada(db_session, e, product_id):
    return await db_session.scalar(
        text(
            "INSERT INTO ordenes_compra (proveedor_id, tienda_id, empleado_id, estado) "
            "VALUES (:pr, :t, :emp, 'aprobada') RETURNING orden_id"
        ),
        {"pr": e["proveedor_id"], "t": e["tienda_id"], "emp": e["encargado_id"]},
    )


async def test_escenario_6_recepcion_dos_lotes_y_venta_fefo(
    client, escenario_inventario, auth_reponedor, auth_cajero, db_session
):
    e = escenario_inventario
    pid = e["product_us2"]

    orden_1 = await _orden_aprobada(db_session, e, pid)
    orden_2 = await _orden_aprobada(db_session, e, pid)
    await db_session.flush()

    # Lote que vence PRONTO
    r1 = await client.post(
        "/api/inventario/recepciones",
        json={
            "orden_id": orden_1,
            "product_id": pid,
            "tienda_id": e["tienda_id"],
            "cantidad": 20,
            "fecha_vencimiento": "2026-09-20",
        },
        headers=auth_reponedor,
    )
    # Lote que vence MÁS TARDE
    r2 = await client.post(
        "/api/inventario/recepciones",
        json={
            "orden_id": orden_2,
            "product_id": pid,
            "tienda_id": e["tienda_id"],
            "cantidad": 30,
            "fecha_vencimiento": "2026-12-31",
        },
        headers=auth_reponedor,
    )
    assert r1.status_code == 201 and r2.status_code == 201, (r1.text, r2.text)
    lote_pronto, lote_tarde = r1.json()["lote_id"], r2.json()["lote_id"]

    # GET /lotes prioriza el que vence antes
    lotes = (
        await client.get(
            "/api/inventario/lotes",
            params={"product_id": pid, "tienda_id": e["tienda_id"]},
            headers=auth_reponedor,
        )
    ).json()
    assert [lo["lote_id"] for lo in lotes["items"]][:2] == [lote_pronto, lote_tarde]

    # Venta de 15 (sólo alcanza el primer lote de 20)
    venta = (
        await client.post(
            "/api/ventas",
            json={"tienda_id": e["tienda_id"], "cajero_id": e["cajero_id"]},
            headers=auth_cajero,
        )
    ).json()
    await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas",
        json={"product_id": pid, "cantidad": 15},
        headers=auth_cajero,
    )
    conf = await client.post(
        f"/api/ventas/{venta['venta_id']}/confirmar",
        json={"medio_pago_id": e["medio_efectivo"]},
        headers=auth_cajero,
    )
    assert conf.status_code == 200, conf.text

    saldo_pronto = await db_session.scalar(
        text("SELECT cantidad_disponible FROM lotes WHERE lote_id = :l"), {"l": lote_pronto}
    )
    saldo_tarde = await db_session.scalar(
        text("SELECT cantidad_disponible FROM lotes WHERE lote_id = :l"), {"l": lote_tarde}
    )
    assert saldo_pronto == 5  # 20 - 15, se consumió el que vence antes (FEFO)
    assert saldo_tarde == 30  # intacto
