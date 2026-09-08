"""T045 — integración US5: Escenario 6 de quickstart.md.

Definir umbral → mermas registradas (001) → el seguimiento semanal muestra el
porcentaje frente al umbral, sin bloquear ninguna operación (FR-019).
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_seguimiento_semanal_muestra_porcentaje_frente_al_umbral(
    client, escenario_caja, auth_caja_ops, auth_encargado, db_session
):
    e = escenario_caja
    hoy = date.today()
    iso = hoy.isocalendar()

    umbral = await client.put(
        "/api/caja/umbral-merma/TEST CAT",
        json={"porcentaje_umbral": "5.0"},
        headers=auth_caja_ops,
    )
    assert umbral.status_code == 200, umbral.text

    # ventas confirmadas de la categoría en la semana: 1000 de valor
    venta_id = await db_session.scalar(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
            "VALUES (:t, :c, :f, :sem, 1000, 'confirmada') RETURNING venta_id"
        ),
        {
            "t": e["tienda_id"],
            "c": e["cajero_id"],
            "f": datetime.now(UTC).replace(tzinfo=None),
            "sem": iso.week,
        },
    )
    await db_session.execute(
        text(
            "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
            "VALUES (:v, :p, 100, 10.00)"
        ),
        {"v": venta_id, "p": e["product_id"]},
    )
    # merma de la categoría en la misma semana: 80 de valor → 8 %
    await db_session.execute(
        text(
            "INSERT INTO mermas (product_id, tienda_id, cantidad, causa, valor, "
            "empleado_id, fecha) VALUES (:p, :t, 8, 'caducidad', 80.00, :emp, :f)"
        ),
        {"p": e["product_id"], "t": e["tienda_id"], "emp": e["cajero_id"], "f": hoy},
    )
    await db_session.flush()

    seguimiento = await client.get(
        f"/api/caja/tiendas/{e['tienda_id']}/seguimiento-merma-semanal",
        params={"semana": iso.week, "anio": iso.year},
        headers=auth_encargado,
    )
    assert seguimiento.status_code == 200, seguimiento.text
    fila = next(f for f in seguimiento.json() if f["product_category"] == "TEST CAT")
    assert Decimal(fila["porcentaje_merma_acumulado"]) == Decimal("8.00")
    assert Decimal(fila["porcentaje_umbral"]) == Decimal("5.00")
    assert fila["supera_umbral"] is True

    # FR-019: superar el umbral no bloquea registrar otra merma
    otra = await db_session.execute(
        text(
            "INSERT INTO mermas (product_id, tienda_id, cantidad, causa, valor, empleado_id) "
            "VALUES (:p, :t, 1, 'rotura', 10.00, :emp) RETURNING merma_id"
        ),
        {"p": e["product_id"], "t": e["tienda_id"], "emp": e["cajero_id"]},
    )
    assert otra.scalar_one() is not None
