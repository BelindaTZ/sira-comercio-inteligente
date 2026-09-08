"""T021 — integración US2: Escenario 2 de quickstart.md.

Alta → disponible en punto de venta → baja → ya no disponible → ventas históricas
con ese medio de pago intactas.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_alta_baja_sin_afectar_ventas_registradas(
    client, escenario_pagos, auth_caja_ti, auth_cajero, db_session
):
    e = escenario_pagos

    # venta histórica con el medio "Tarjeta" ya existente
    venta_id = await db_session.scalar(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado, "
            "medio_pago_id) VALUES (:t, :c, CURRENT_TIMESTAMP, 1, 10, 'confirmada', :mp) "
            "RETURNING venta_id"
        ),
        {"t": e["tienda_id"], "c": e["cajero_id"], "mp": e["medio_tarjeta"]},
    )
    await db_session.flush()

    alta = await client.post(
        "/api/ventas/medios-pago", json={"nombre": "Billetera XYZ"}, headers=auth_caja_ti
    )
    medio_id = alta.json()["medio_pago_id"]

    disp = await client.get("/api/ventas/medios-pago/disponibles", headers=auth_cajero)
    assert "Billetera XYZ" in [m["nombre"] for m in disp.json()]

    await client.patch(f"/api/ventas/medios-pago/{e['medio_tarjeta']}/baja", headers=auth_caja_ti)

    disp2 = await client.get("/api/ventas/medios-pago/disponibles", headers=auth_cajero)
    nombres = [m["nombre"] for m in disp2.json()]
    assert "Tarjeta" not in nombres
    assert "Billetera XYZ" in nombres  # el nuevo sigue disponible

    # la venta histórica con "Tarjeta" quedó intacta
    mp_venta = await db_session.scalar(
        text("SELECT medio_pago_id FROM ventas WHERE venta_id = :v"), {"v": venta_id}
    )
    assert mp_venta == e["medio_tarjeta"]

    # el listado admin sigue mostrando el medio dado de baja
    todos = await client.get("/api/ventas/medios-pago", headers=auth_caja_ti)
    tarjeta = next(m for m in todos.json() if m["medio_pago_id"] == e["medio_tarjeta"])
    assert tarjeta["aprobado"] is False and tarjeta["fecha_baja"] is not None
    assert medio_id in [m["medio_pago_id"] for m in todos.json()]
