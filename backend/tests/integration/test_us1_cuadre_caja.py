"""T012 — integración US1: Escenarios 1 y 2 de quickstart.md.

Apertura → ventas → cuadre con diferencia calculada sola → el Encargado de Tienda
ve el estado de todas las cajas de su tienda en una sola consulta.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _venta(db_session, tienda_id, cajero_id, total):
    vid = await db_session.scalar(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
            "VALUES (:t, :c, :f, 1, :total, 'confirmada') RETURNING venta_id"
        ),
        {
            "t": tienda_id,
            "c": cajero_id,
            "f": datetime.now(UTC).replace(tzinfo=None),
            "total": total,
        },
    )
    await db_session.flush()
    return vid


async def test_cuadre_horario_de_punta_a_punta(
    client, escenario_caja, auth_cajero, auth_encargado, db_session
):
    e = escenario_caja

    ap = await client.post(
        "/api/caja/apertura",
        json={"caja_id": e["caja_1"], "fondo_inicial": "200.00"},
        headers=auth_cajero,
    )
    assert ap.status_code == 201, ap.text

    await _venta(db_session, e["tienda_id"], e["cajero_id"], Decimal("300.00"))
    await _venta(db_session, e["tienda_id"], e["cajero_id"], Decimal("180.00"))

    cierre = await client.post(
        "/api/caja/cierre",
        json={"caja_id": e["caja_1"], "total_registrado": "480.00"},
        headers=auth_cajero,
    )
    assert cierre.status_code == 201, cierre.text
    assert Decimal(cierre.json()["total_esperado"]) == Decimal("480.00")
    assert Decimal(cierre.json()["diferencia"]) == Decimal("0.00")
    assert cierre.json()["marcado_para_revision"] is False

    # segundo cuadre del mismo turno con faltante: sólo cuenta la venta nueva
    await _venta(db_session, e["tienda_id"], e["cajero_id"], Decimal("50.00"))
    cierre2 = await client.post(
        "/api/caja/cierre",
        json={"caja_id": e["caja_1"], "total_registrado": "40.00"},
        headers=auth_cajero,
    )
    assert Decimal(cierre2.json()["total_esperado"]) == Decimal("50.00")
    assert Decimal(cierre2.json()["diferencia"]) == Decimal("-10.00")
    assert cierre2.json()["marcado_para_revision"] is True

    # Escenario 2: el Encargado ve el cuadre de todas las cajas de su tienda
    consolidado = await client.get(
        "/api/caja/cierres", params={"tienda_id": e["tienda_id"]}, headers=auth_encargado
    )
    assert consolidado.status_code == 200, consolidado.text
    fila = next(f for f in consolidado.json() if f["caja_id"] == e["caja_1"])
    assert fila["cierre_id"] == cierre2.json()["cierre_id"]  # el más reciente del día
    assert fila["marcado_para_revision"] is True
