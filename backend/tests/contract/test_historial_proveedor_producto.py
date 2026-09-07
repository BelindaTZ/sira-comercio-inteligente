"""T090 — contrato GET /api/compras/proveedores/{id}/productos y
GET /api/compras/productos/{id}/proveedores (FR-044, Ronda 11).

Ambos endpoints son de solo lectura y derivan de `ordenes_compra` /
`orden_compra_detalle` — no hay tabla ni catálogo maestro nuevo.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _orden_con_lineas(db_session, e, proveedor_id, lineas):
    orden_id = await db_session.scalar(
        text(
            "INSERT INTO ordenes_compra (proveedor_id, tienda_id, empleado_id, estado, fecha) "
            "VALUES (:pr, :t, :emp, 'aprobada', CURRENT_DATE) RETURNING orden_id"
        ),
        {"pr": proveedor_id, "t": e["tienda_id"], "emp": e["jefe_ops_id"]},
    )
    for pid, cant in lineas:
        await db_session.execute(
            text(
                "INSERT INTO orden_compra_detalle (orden_id, product_id, cantidad, costo_unitario) "
                "VALUES (:o, :p, :c, 1.00)"
            ),
            {"o": orden_id, "p": pid, "c": cant},
        )
    await db_session.flush()
    return orden_id


async def test_productos_de_un_proveedor(client, escenario_compras, auth_jefe_ops, db_session):
    e = escenario_compras
    await _orden_con_lineas(db_session, e, e["proveedor_id"], [(e["product_id"], 10)])
    await _orden_con_lineas(
        db_session, e, e["proveedor_id"], [(e["product_id"], 5), (e["product_us2"], 3)]
    )

    resp = await client.get(
        f"/api/compras/proveedores/{e['proveedor_id']}/productos", headers=auth_jefe_ops
    )
    assert resp.status_code == 200, resp.text
    por_producto = {row["product_id"]: row for row in resp.json()}
    assert por_producto[e["product_id"]]["cantidad_total"] == 15
    assert por_producto[e["product_id"]]["ordenes"] == 2
    assert e["product_us2"] in por_producto


async def test_proveedores_de_un_producto(client, escenario_compras, auth_jefe_ops, db_session):
    e = escenario_compras
    otro_proveedor = await db_session.scalar(
        text("INSERT INTO proveedores (nombre) VALUES ('Proveedor B') RETURNING proveedor_id")
    )
    await _orden_con_lineas(db_session, e, e["proveedor_id"], [(e["product_id"], 8)])
    await _orden_con_lineas(db_session, e, otro_proveedor, [(e["product_id"], 4)])

    resp = await client.get(
        f"/api/compras/productos/{e['product_id']}/proveedores", headers=auth_jefe_ops
    )
    assert resp.status_code == 200, resp.text
    ids = {row["proveedor_id"] for row in resp.json()}
    assert {e["proveedor_id"], otro_proveedor} <= ids


async def test_proveedor_inexistente_da_404(client, escenario_compras, auth_jefe_ops):
    resp = await client.get("/api/compras/proveedores/99999999/productos", headers=auth_jefe_ops)
    assert resp.status_code == 404


async def test_producto_sin_historial_devuelve_lista_vacia(
    client, escenario_compras, auth_jefe_ops
):
    e = escenario_compras
    resp = await client.get(
        f"/api/compras/productos/{e['product_id']}/proveedores", headers=auth_jefe_ops
    )
    assert resp.status_code == 200
    assert resp.json() == []
