"""Integration tests — ciclo completo de un traslado entre tiendas (feature 012).

Cubre T012 (US1), T021-T023 (US2) y T033-T035 (US3) de tasks.md, siguiendo los
escenarios de `quickstart.md`.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _inventario(db_session, product_id: int, tienda_id: int) -> int:
    return (
        await db_session.scalar(
            text(
                "SELECT cantidad_disponible FROM inventario "
                "WHERE product_id = :p AND tienda_id = :t"
            ),
            {"p": product_id, "t": tienda_id},
        )
    ) or 0


async def _movimientos(db_session, traslado_id: int, tipo: str) -> int:
    return await db_session.scalar(
        text(
            "SELECT COUNT(*) FROM movimientos_inventario "
            "WHERE referencia_tabla = 'traslados_stock' AND referencia_id = :id AND tipo = :tipo"
        ),
        {"id": traslado_id, "tipo": tipo},
    )


# ---------------------------------------------------------------- US1 (T012)
async def test_disponibilidad_en_una_sola_respuesta(
    client, escenario_traslados, auth_traslados_ops
):
    e = escenario_traslados
    resp = await client.get(
        f"/api/traslados/productos/{e['product_id']}/disponibilidad-sucursales",
        headers=auth_traslados_ops,
    )
    assert resp.status_code == 200
    tiendas = {d["tienda_id"] for d in resp.json()["disponibilidad"]}
    assert {e["tienda_a"], e["tienda_b"]} <= tiendas  # ambas llegan juntas


# ---------------------------------------------------------------- US2 (T021)
async def test_ciclo_solicitud_aprobacion_descuenta_origen(client, db_session, escenario_traslados):
    e = escenario_traslados
    antes = await _inventario(db_session, e["product_id"], e["tienda_a"])

    r = await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_b"],
            "cantidad": 30,
        },
        headers=_bearer(e["token_encargado_b"]),
    )
    tid = r.json()["traslado_id"]

    aprob = await client.patch(
        f"/api/traslados/{tid}/resolucion",
        json={"decision": "aprobar"},
        headers=_bearer(e["token_encargado_a"]),
    )
    assert aprob.status_code == 200

    assert await _inventario(db_session, e["product_id"], e["tienda_a"]) == antes - 30
    assert await _movimientos(db_session, tid, "traslado_salida") >= 1


# ---------------------------------------------------------------- US2 (T022)
async def test_aprobar_por_encima_del_stock_da_409(client, escenario_traslados):
    e = escenario_traslados
    r = await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_b"],
            "cantidad": 5000,
        },
        headers=_bearer(e["token_encargado_b"]),
    )
    tid = r.json()["traslado_id"]
    resp = await client.patch(
        f"/api/traslados/{tid}/resolucion",
        json={"decision": "aprobar"},
        headers=_bearer(e["token_encargado_a"]),
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["details"]["stock_disponible"] == 200


# ---------------------------------------------------------------- US2 (T023)
async def test_rechazo_no_toca_inventario(client, db_session, escenario_traslados):
    e = escenario_traslados
    a_antes = await _inventario(db_session, e["product_id"], e["tienda_a"])

    r = await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_b"],
            "cantidad": 12,
        },
        headers=_bearer(e["token_encargado_b"]),
    )
    tid = r.json()["traslado_id"]
    rech = await client.patch(
        f"/api/traslados/{tid}/resolucion",
        json={"decision": "rechazar", "motivo": "no"},
        headers=_bearer(e["token_encargado_a"]),
    )
    assert rech.status_code == 200 and rech.json()["estado"] == "rechazado"
    assert await _inventario(db_session, e["product_id"], e["tienda_a"]) == a_antes
    assert await _movimientos(db_session, tid, "traslado_salida") == 0


# ---------------------------------------------------------------- US3 (T033)
async def test_recepcion_incrementa_destino(client, db_session, escenario_traslados):
    e = escenario_traslados
    b_antes = await _inventario(db_session, e["product_id"], e["tienda_b"])

    r = await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_b"],
            "cantidad": 25,
        },
        headers=_bearer(e["token_encargado_b"]),
    )
    tid = r.json()["traslado_id"]
    await client.patch(
        f"/api/traslados/{tid}/resolucion",
        json={"decision": "aprobar"},
        headers=_bearer(e["token_encargado_a"]),
    )
    rec = await client.patch(
        f"/api/traslados/{tid}/recepcion", headers=_bearer(e["token_encargado_b"])
    )
    assert rec.status_code == 200

    assert await _inventario(db_session, e["product_id"], e["tienda_b"]) == b_antes + 25
    assert await _movimientos(db_session, tid, "traslado_entrada") == 1


# ---------------------------------------------------------------- US3 (T034)
async def test_lote_destino_hereda_fecha_vencimiento(client, db_session, escenario_traslados):
    e = escenario_traslados
    r = await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_b"],
            "cantidad": 10,
        },
        headers=_bearer(e["token_encargado_b"]),
    )
    tid = r.json()["traslado_id"]
    await client.patch(
        f"/api/traslados/{tid}/resolucion",
        json={"decision": "aprobar"},
        headers=_bearer(e["token_encargado_a"]),
    )
    await client.patch(f"/api/traslados/{tid}/recepcion", headers=_bearer(e["token_encargado_b"]))

    venc_lote_nuevo = await db_session.scalar(
        text(
            "SELECT l.fecha_vencimiento "
            "FROM movimientos_inventario m JOIN lotes l ON l.lote_id = m.lote_id "
            "WHERE m.referencia_tabla = 'traslados_stock' AND m.referencia_id = :id "
            "AND m.tipo = 'traslado_entrada'"
        ),
        {"id": tid},
    )
    assert venc_lote_nuevo is not None
    assert venc_lote_nuevo.isoformat() == e["fecha_vencimiento"]


# ---------------------------------------------------------------- US3 (T035)
async def test_cancelacion_en_solicitado_no_toca_inventario(
    client, db_session, escenario_traslados
):
    e = escenario_traslados
    a_antes = await _inventario(db_session, e["product_id"], e["tienda_a"])
    b_antes = await _inventario(db_session, e["product_id"], e["tienda_b"])

    r = await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_b"],
            "cantidad": 8,
        },
        headers=_bearer(e["token_encargado_b"]),
    )
    tid = r.json()["traslado_id"]
    canc = await client.patch(
        f"/api/traslados/{tid}/cancelacion", headers=_bearer(e["token_encargado_b"])
    )
    assert canc.status_code == 200 and canc.json()["estado"] == "cancelado"
    assert canc.json()["fecha_cancelacion"] is not None
    assert await _inventario(db_session, e["product_id"], e["tienda_a"]) == a_antes
    assert await _inventario(db_session, e["product_id"], e["tienda_b"]) == b_antes
