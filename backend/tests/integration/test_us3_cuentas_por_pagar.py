"""T049 — integración US3: Escenario 5 de quickstart.md.

Ciclo completo: orden aprobada → recepción (orden 'recibida') → factura →
pago parcial con doble autorización → factura 'pagada_parcial'.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_escenario_5_ciclo_completo_orden_a_pago(
    client, escenario_compras, auth_reponedor, auth_jefe_ops, auth_jefe_fin
):
    e = escenario_compras

    # 1. Orden aprobada (escenario_inventario ya trae una 'aprobada' — la usamos)
    orden_id = e["orden_id"]

    # 2. Recepción → la orden pasa a 'recibida'
    rec = await client.post(
        "/api/inventario/recepciones",
        json={
            "orden_id": orden_id,
            "product_id": e["product_us2"],
            "tienda_id": e["tienda_id"],
            "cantidad": 100,
        },
        headers=auth_reponedor,
    )
    assert rec.status_code == 201, rec.text

    # 3. Factura del proveedor (vencimiento a 30 días)
    fac = await client.post(
        "/api/compras/facturas",
        json={
            "orden_id": orden_id,
            "numero_factura": "FP-2026-777",
            "monto_total": "120.00",
            "fecha_emision": "2026-09-01",
            "fecha_vencimiento": "2026-10-01",
            "empleado_registra_id": e["jefe_fin_id"],
        },
        headers=auth_jefe_fin,
    )
    assert fac.status_code == 201, fac.text
    factura = fac.json()
    assert factura["estado"] == "pendiente"
    assert factura["saldo"] == "120.00"

    # 4. Pago parcial: lo confirma el AUTORIZADOR (Jefe de Operaciones), que no es
    #    quien lo registró (Jefe de Finanzas) — control de doble persona (SC-009, T073).
    pago = await client.post(
        f"/api/compras/facturas/{factura['factura_id']}/pagos",
        json={
            "monto": "70.00",
            "medio_pago_id": e["medio_efectivo"],
            "referencia": "TRANSF-9911",
            "empleado_registra_id": e["jefe_fin_id"],
            "empleado_autoriza_id": e["jefe_ops_id"],
        },
        headers=auth_jefe_ops,
    )
    assert pago.status_code == 200, pago.text
    assert pago.json()["factura_estado"] == "pagada_parcial"

    # 5. Resumen de cuentas por pagar refleja el saldo pendiente
    resumen = await client.get(
        "/api/compras/facturas/resumen",
        params={"desde": "2026-09-01", "hasta": "2026-09-30"},
        headers=auth_jefe_fin,
    )
    assert resumen.status_code == 200, resumen.text
    assert resumen.json()["facturas_abiertas"] >= 1
