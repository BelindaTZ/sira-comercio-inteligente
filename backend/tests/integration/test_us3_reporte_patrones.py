"""T030 — integración US3: Escenario 4 de quickstart.md.

Cuadres con diferencia negativa repetida de un cajero + un ajuste de inventario
anómalo → reporte mensual agrupado por cajero/turno → apertura de un incidente de
fraude desde ahí.
"""

from datetime import UTC, date, datetime
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


async def test_reporte_mensual_agrupa_y_permite_escalar(
    client, escenario_caja, auth_cajero, auth_caja_finanzas, db_session
):
    e = escenario_caja
    hoy = date.today()

    await client.post(
        "/api/caja/apertura",
        json={"caja_id": e["caja_1"], "fondo_inicial": "0.00"},
        headers=auth_cajero,
    )
    cierre_ids = []
    for _ in range(3):
        await _venta(db_session, e["tienda_id"], e["cajero_id"], Decimal("100.00"))
        r = await client.post(
            "/api/caja/cierre",
            json={"caja_id": e["caja_1"], "total_registrado": "90.00"},
            headers=auth_cajero,
        )
        assert r.status_code == 201, r.text
        assert Decimal(r.json()["diferencia"]) == Decimal("-10.00")
        cierre_ids.append(r.json()["cierre_id"])

    # ajuste de inventario de 001 con faltante grande (diferencia -20, umbral 10)
    await db_session.execute(
        text(
            "INSERT INTO ajustes_inventario "
            "(product_id, tienda_id, cantidad_sistema, cantidad_fisica, empleado_id, fecha) "
            "VALUES (:p, :t, 100, 80, :emp, :f)"
        ),
        {"p": e["product_id"], "t": e["tienda_id"], "emp": e["cajero_id"], "f": hoy},
    )
    await db_session.flush()

    reporte = await client.get(
        "/api/caja/reporte-diferencias",
        params={"mes": hoy.month, "anio": hoy.year},
        headers=auth_caja_finanzas,
    )
    assert reporte.status_code == 200, reporte.text
    data = reporte.json()

    turnos_cajero = [c for c in data["cuadres"] if c["cajero_id"] == e["cajero_id"]]
    assert len(turnos_cajero) == 1  # un solo turno, no tres filas sueltas
    assert Decimal(turnos_cajero[0]["suma_diferencias"]) == Decimal("-30.00")
    assert turnos_cajero[0]["cantidad_cuadres_con_diferencia"] == 3

    assert any(a["tienda_id"] == e["tienda_id"] for a in data["ajustes_senalados"])

    incidente = await client.post(
        "/api/caja/incidentes-fraude",
        json={
            "empleado_id": e["cajero_id"],
            "cierre_id": cierre_ids[0],
            "descripcion": "Faltante repetido de 10 en cada cuadre del turno",
        },
        headers=auth_caja_finanzas,
    )
    assert incidente.status_code == 201, incidente.text
    assert incidente.json()["estado"] == "abierto"
    assert incidente.json()["cierre_id"] == cierre_ids[0]
