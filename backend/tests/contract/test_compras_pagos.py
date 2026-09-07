"""T047 — contrato POST /api/compras/facturas/{id}/pagos (FR-034, SC-009).

403 si `empleado_registra_id == empleado_autoriza_id`; el estado de la factura se
recalcula (`pagada_parcial` / `pagada`) al confirmar cada pago (FR-035).
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _orden_recibida_con_factura(client, db_session, e, auth_fin):
    orden_id = await db_session.scalar(
        text(
            "INSERT INTO ordenes_compra (proveedor_id, tienda_id, empleado_id, estado) "
            "VALUES (:pr, :t, :emp, 'recibida') RETURNING orden_id"
        ),
        {"pr": e["proveedor_id"], "t": e["tienda_id"], "emp": e["jefe_ops_id"]},
    )
    await db_session.flush()
    factura = (
        await client.post(
            "/api/compras/facturas",
            json={
                "orden_id": orden_id,
                "numero_factura": "F-001-0001",
                "monto_total": "100.00",
                "fecha_emision": "2026-09-01",
                "fecha_vencimiento": "2026-10-01",
                "empleado_registra_id": e["jefe_fin_id"],
            },
            headers=auth_fin,
        )
    ).json()
    return factura


async def test_pago_con_mismo_empleado_registra_y_autoriza_da_403(
    client, escenario_compras, auth_jefe_fin, db_session
):
    e = escenario_compras
    factura = await _orden_recibida_con_factura(client, db_session, e, auth_jefe_fin)
    resp = await client.post(
        f"/api/compras/facturas/{factura['factura_id']}/pagos",
        json={
            "monto": "50.00",
            "medio_pago_id": e["medio_efectivo"],
            "empleado_registra_id": e["jefe_fin_id"],
            "empleado_autoriza_id": e["jefe_fin_id"],
        },
        headers=auth_jefe_fin,
    )
    assert resp.status_code == 403, resp.text


async def test_pagos_parciales_recalculan_el_estado(
    client, escenario_compras, auth_jefe_fin, auth_jefe_ops, db_session
):
    e = escenario_compras
    factura = await _orden_recibida_con_factura(client, db_session, e, auth_jefe_fin)

    r1 = await client.post(
        f"/api/compras/facturas/{factura['factura_id']}/pagos",
        json={
            "monto": "40.00",
            "medio_pago_id": e["medio_efectivo"],
            "empleado_registra_id": e["jefe_fin_id"],
            "empleado_autoriza_id": e["jefe_ops_id"],
        },
        headers=auth_jefe_ops,
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["factura_estado"] == "pagada_parcial"

    r2 = await client.post(
        f"/api/compras/facturas/{factura['factura_id']}/pagos",
        json={
            "monto": "60.00",
            "medio_pago_id": e["medio_efectivo"],
            "empleado_registra_id": e["jefe_fin_id"],
            "empleado_autoriza_id": e["jefe_ops_id"],
        },
        headers=auth_jefe_ops,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["factura_estado"] == "pagada"


async def test_pago_que_excede_el_saldo_es_rechazado(
    client, escenario_compras, auth_jefe_fin, auth_jefe_ops, db_session
):
    e = escenario_compras
    factura = await _orden_recibida_con_factura(client, db_session, e, auth_jefe_fin)
    resp = await client.post(
        f"/api/compras/facturas/{factura['factura_id']}/pagos",
        json={
            "monto": "150.00",
            "medio_pago_id": e["medio_efectivo"],
            "empleado_registra_id": e["jefe_fin_id"],
            "empleado_autoriza_id": e["jefe_ops_id"],
        },
        headers=auth_jefe_ops,
    )
    assert resp.status_code == 409, resp.text


async def test_factura_duplicada_da_409(client, escenario_compras, auth_jefe_fin, db_session):
    e = escenario_compras
    factura = await _orden_recibida_con_factura(client, db_session, e, auth_jefe_fin)
    resp = await client.post(
        "/api/compras/facturas",
        json={
            "orden_id": factura["orden_id"],
            "numero_factura": "F-001-0001",
            "monto_total": "10.00",
            "fecha_emision": "2026-09-01",
            "fecha_vencimiento": "2026-10-01",
            "empleado_registra_id": e["jefe_fin_id"],
        },
        headers=auth_jefe_fin,
    )
    assert resp.status_code == 409, resp.text
