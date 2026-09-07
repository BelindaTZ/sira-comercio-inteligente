"""T048 — integración US3: Escenario 4 de quickstart.md (alerta + sugerencia).

1. Se vende un producto hasta dejarlo por debajo del punto de reposición.
2. El job diario calcula el punto y genera una alerta `pendiente` (sin duplicar).
3. La sugerencia semanal incluye el producto; aprobar una orden que difiere exige
   `motivo_desviacion` (FR-024).
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _vender(client, e, auth, cantidad):
    venta = (
        await client.post(
            "/api/ventas",
            json={"tienda_id": e["tienda_id"], "cajero_id": e["cajero_id"]},
            headers=auth,
        )
    ).json()
    await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas",
        json={"product_id": e["product_id"], "cantidad": cantidad},
        headers=auth,
    )
    await client.post(
        f"/api/ventas/{venta['venta_id']}/confirmar",
        json={"medio_pago_id": e["medio_efectivo"]},
        headers=auth,
    )


async def test_escenario_4_alerta_y_sugerencia(
    client, escenario_compras, auth_cajero, auth_jefe_ops, db_session
):
    e = escenario_compras
    # escenario_pos: inventario 100, lotes 40 + 60. Vendemos 95 (venta reciente).
    await _vender(client, e, auth_cajero, 60)
    await _vender(client, e, auth_cajero, 35)

    # Job de reposición: con ~95 u vendidas en la ventana, el punto sube muy por
    # encima de las 5 unidades que quedan → alerta.
    job = await client.post(
        "/api/inventario/jobs/reposicion",
        params={"tienda_id": e["tienda_id"]},
        headers=auth_jefe_ops,
    )
    assert job.status_code == 200, job.text
    generadas = {g["product_id"] for g in job.json()["alertas_generadas"]}
    assert e["product_id"] in generadas

    # No duplica al re-ejecutar
    job2 = await client.post(
        "/api/inventario/jobs/reposicion",
        params={"tienda_id": e["tienda_id"]},
        headers=auth_jefe_ops,
    )
    assert e["product_id"] not in {g["product_id"] for g in job2.json()["alertas_generadas"]}

    activas = await db_session.scalar(
        text(
            "SELECT COUNT(*) FROM alertas_inventario "
            "WHERE product_id = :p AND tienda_id = :t AND tipo = 'reposicion' "
            "AND estado = 'pendiente'"
        ),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    assert activas == 1

    # Sugerencia semanal incluye el producto
    sug = await client.get(
        "/api/compras/sugerencias", params={"tienda_id": e["tienda_id"]}, headers=auth_jefe_ops
    )
    assert sug.status_code == 200
    assert e["product_id"] in {s["product_id"] for s in sug.json()}

    # Aprobar una orden que difiere de la sugerencia exige motivo (FR-024)
    resp = await client.post(
        "/api/compras/ordenes",
        json={
            "proveedor_id": e["proveedor_id"],
            "tienda_id": e["tienda_id"],
            "empleado_id": e["jefe_ops_id"],
            "lineas": [{"product_id": e["product_id"], "cantidad": 999, "costo_unitario": "1.00"}],
        },
        headers=auth_jefe_ops,
    )
    assert resp.status_code == 422
