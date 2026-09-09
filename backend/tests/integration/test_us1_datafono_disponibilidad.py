"""T012 — integración US1: Escenario 1 de quickstart.md.

Marcar fuera de servicio → advertencia en el flujo de cobro sin bloquear otro
medio de pago → restablecer con reevaluación de conformidad (006).
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_disponibilidad_diaria_de_punta_a_punta(
    client, escenario_pagos, auth_encargado, auth_cajero, db_session
):
    e = escenario_pagos

    fuera = await client.patch(
        f"/api/caja/datafonos/{e['datafono_viejo']}/fuera-servicio",
        json={"motivo": "sin respuesta en la verificación diaria"},
        headers=auth_encargado,
    )
    assert fuera.status_code == 200 and fuera.json()["estado"] == "fuera_servicio"

    disp = await client.get(
        f"/api/ventas/cajas/{e['caja_1']}/datafono-disponible", headers=auth_cajero
    )
    assert disp.json()["disponible"] is False

    # una venta en efectivo en esa misma caja NO se bloquea
    iniciar = await client.post(
        "/api/ventas",
        json={"tienda_id": e["tienda_id"], "cajero_id": e["cajero_id"]},
        headers=auth_cajero,
    )
    assert iniciar.status_code == 201, iniciar.text
    venta_id = iniciar.json()["venta_id"]
    await client.post(
        f"/api/ventas/{venta_id}/lineas",
        json={"product_id": e["product_id"], "cantidad": 1},
        headers=auth_cajero,
    )
    confirmar = await client.post(
        f"/api/ventas/{venta_id}/confirmar",
        json={"medio_pago_id": e["medio_efectivo"]},
        headers=auth_cajero,
    )
    assert confirmar.status_code == 200, confirmar.text
    assert confirmar.json()["estado"] == "confirmada"

    # restablecer: firmware 2.9.0 < estándar 3.0.0 → requiere_actualizacion
    rest = await client.patch(
        f"/api/caja/datafonos/{e['datafono_viejo']}/restablecer", headers=auth_encargado
    )
    assert rest.json()["estado"] == "requiere_actualizacion"

    estado_final = await db_session.scalar(
        text("SELECT estado FROM datafonos WHERE datafono_id = :d"), {"d": e["datafono_viejo"]}
    )
    assert estado_final == "requiere_actualizacion"
