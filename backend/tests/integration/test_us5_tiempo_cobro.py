"""T041 (impl) + Escenario 5 de quickstart.md — medición del tiempo de cobro.

Venta en vivo → duración calculada sin intervención manual → revisión semanal por
caja (Encargado de Tienda) y mensual por tienda (Jefe Comercial). Una venta
anulada y una venta sembrada (sin `fecha_inicio_cobro`) quedan excluidas.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _venta_en_vivo(client, e, headers, anular=False):
    iniciar = await client.post(
        "/api/ventas",
        json={"tienda_id": e["tienda_id"], "cajero_id": e["cajero_id"]},
        headers=headers,
    )
    venta_id = iniciar.json()["venta_id"]
    await client.post(
        f"/api/ventas/{venta_id}/lineas",
        json={"product_id": e["product_id"], "cantidad": 1},
        headers=headers,
    )
    await client.post(
        f"/api/ventas/{venta_id}/confirmar",
        json={"medio_pago_id": e["medio_efectivo"]},
        headers=headers,
    )
    if anular:
        await client.post(
            f"/api/ventas/{venta_id}/anular",
            json={"empleado_id": e["encargado_id"], "motivo": "prueba"},
            headers=headers,
        )
    return venta_id


async def test_tiempo_cobro_semanal_y_mensual(
    client, escenario_pagos, auth_cajero, auth_encargado, auth_pagos_comercial, db_session
):
    e = escenario_pagos
    ahora = datetime.now(UTC)
    semana = ahora.isocalendar().week

    # vincula la caja al cajero (research: ventas no tiene caja_id, el vínculo
    # vive en apertura_caja de 006)
    await client.post(
        "/api/caja/apertura",
        json={"caja_id": e["caja_1"], "fondo_inicial": "0"},
        headers=auth_cajero,
    )

    await _venta_en_vivo(client, e, auth_cajero)
    await _venta_en_vivo(client, e, auth_cajero)
    await _venta_en_vivo(client, e, auth_cajero, anular=True)  # excluida (FR-018)

    # venta sembrada sin fecha_inicio_cobro → excluida
    await db_session.execute(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
            "VALUES (:t, :c, CURRENT_TIMESTAMP, :sem, 5, 'confirmada')"
        ),
        {"t": e["tienda_id"], "c": e["cajero_id"], "sem": semana},
    )
    await db_session.flush()

    semanal = await client.get(
        f"/api/ventas/cajas/{e['caja_1']}/tiempo-cobro-semanal",
        params={"semana": semana, "anio": ahora.year},
        headers=auth_encargado,
    )
    assert semanal.status_code == 200, semanal.text
    assert semanal.json()["cantidad_ventas_consideradas"] == 2  # 3 en vivo − 1 anulada
    assert semanal.json()["duracion_promedio_segundos"] is not None

    mensual = await client.get(
        "/api/ventas/tiendas/tiempo-cobro-mensual",
        params={"mes": ahora.month, "anio": ahora.year},
        headers=auth_pagos_comercial,
    )
    assert mensual.status_code == 200, mensual.text
    fila = next(f for f in mensual.json() if f["tienda_id"] == e["tienda_id"])
    assert fila["cantidad_ventas_consideradas"] == 2


async def test_cajero_no_ve_reporte_mensual_de_red(client, escenario_pagos, auth_cajero):
    ahora = datetime.now(UTC)
    resp = await client.get(
        "/api/ventas/tiendas/tiempo-cobro-mensual",
        params={"mes": ahora.month, "anio": ahora.year},
        headers=auth_cajero,
    )
    assert resp.status_code == 403, resp.text
