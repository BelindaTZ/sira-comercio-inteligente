"""T011 — contrato de apertura/cuadre de caja (`contracts/caja-mermas-fraude.md`).

Verifica que `total_esperado` se calcula siempre en el backend y nunca se acepta
del cliente (Principio V), y el RBAC de los endpoints de cuadre.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _venta(db_session, *, tienda_id, cajero_id, total, cuando):
    venta_id = await db_session.scalar(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
            "VALUES (:t, :c, :f, 1, :total, 'confirmada') RETURNING venta_id"
        ),
        {"t": tienda_id, "c": cajero_id, "f": cuando, "total": total},
    )
    await db_session.flush()
    return venta_id


async def test_apertura_y_cierre_calculan_la_diferencia_sin_el_cliente(
    client, escenario_caja, auth_cajero, db_session
):
    e = escenario_caja
    ap = await client.post(
        "/api/caja/apertura",
        json={"caja_id": e["caja_1"], "fondo_inicial": "200.00"},
        headers=auth_cajero,
    )
    assert ap.status_code == 201, ap.text
    assert ap.json()["cajero_id"] == e["cajero_id"]

    cuando = datetime.now(UTC).replace(tzinfo=None)
    await _venta(db_session, tienda_id=e["tienda_id"], cajero_id=e["cajero_id"],
                 total=Decimal("120.00"), cuando=cuando)
    await _venta(db_session, tienda_id=e["tienda_id"], cajero_id=e["cajero_id"],
                 total=Decimal("60.00"), cuando=cuando)

    # el cliente intenta colar un total_esperado — debe ser ignorado
    cierre = await client.post(
        "/api/caja/cierre",
        json={"caja_id": e["caja_1"], "total_registrado": "150.00", "total_esperado": "1.00"},
        headers=auth_cajero,
    )
    assert cierre.status_code == 201, cierre.text
    body = cierre.json()
    assert Decimal(body["total_esperado"]) == Decimal("180.00")  # 120 + 60, calculado server-side
    assert Decimal(body["diferencia"]) == Decimal("-30.00")
    assert body["marcado_para_revision"] is True


async def test_cierre_sin_diferencia_no_se_marca(client, escenario_caja, auth_cajero, db_session):
    e = escenario_caja
    await client.post(
        "/api/caja/apertura",
        json={"caja_id": e["caja_2"], "fondo_inicial": "0.00"},
        headers=auth_cajero,
    )
    cuando = datetime.now(UTC).replace(tzinfo=None)
    await _venta(db_session, tienda_id=e["tienda_id"], cajero_id=e["cajero_id"],
                 total=Decimal("42.50"), cuando=cuando)

    cierre = await client.post(
        "/api/caja/cierre",
        json={"caja_id": e["caja_2"], "total_registrado": "42.50"},
        headers=auth_cajero,
    )
    assert cierre.status_code == 201, cierre.text
    assert Decimal(cierre.json()["diferencia"]) == Decimal("0.00")
    assert cierre.json()["marcado_para_revision"] is False


async def test_cierre_sin_apertura_da_conflicto(client, escenario_caja, auth_cajero):
    e = escenario_caja
    resp = await client.post(
        "/api/caja/cierre",
        json={"caja_id": e["caja_1"], "total_registrado": "10.00"},
        headers=auth_cajero,
    )
    assert resp.status_code == 409, resp.text


async def test_jefe_ti_no_puede_cuadrar_caja(client, escenario_caja, auth_caja_ti):
    e = escenario_caja
    resp = await client.post(
        "/api/caja/apertura",
        json={"caja_id": e["caja_1"], "fondo_inicial": "0.00"},
        headers=auth_caja_ti,
    )
    assert resp.status_code == 403, resp.text


async def test_encargado_ve_todas_las_cajas_de_su_tienda(
    client, escenario_caja, auth_cajero, auth_encargado, db_session
):
    e = escenario_caja
    cuando = datetime.now(UTC).replace(tzinfo=None)
    for caja in (e["caja_1"], e["caja_2"]):
        await client.post(
            "/api/caja/apertura",
            json={"caja_id": caja, "fondo_inicial": "0.00"},
            headers=auth_cajero,
        )
        await _venta(db_session, tienda_id=e["tienda_id"], cajero_id=e["cajero_id"],
                     total=Decimal("10.00"), cuando=cuando)
        await client.post(
            "/api/caja/cierre",
            json={"caja_id": caja, "total_registrado": "9.00"},
            headers=auth_cajero,
        )

    resp = await client.get("/api/caja/cierres", headers=auth_encargado)
    assert resp.status_code == 200, resp.text
    cajas = {fila["caja_id"] for fila in resp.json()}
    assert {e["caja_1"], e["caja_2"]}.issubset(cajas)
