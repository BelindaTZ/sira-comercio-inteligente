"""T046 — contrato POST /api/compras/ordenes (FR-024).

`motivo_desviacion` es obligatorio cuando las líneas difieren de la sugerencia
del sistema.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _forzar_sugerencia(db_session, e):
    """Deja el producto por debajo de su punto de reposición para que aparezca
    en la sugerencia semanal."""
    await db_session.execute(
        text(
            "UPDATE inventario SET cantidad_minima = 50, cantidad_disponible = 10 "
            "WHERE product_id = :p AND tienda_id = :t"
        ),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )
    await db_session.flush()
    # sugerida = 50*2 - 10 = 90


async def test_orden_igual_a_la_sugerencia_no_exige_motivo(
    client, escenario_compras, auth_jefe_ops, db_session
):
    e = escenario_compras
    await _forzar_sugerencia(db_session, e)
    resp = await client.post(
        "/api/compras/ordenes",
        json={
            "proveedor_id": e["proveedor_id"],
            "tienda_id": e["tienda_id"],
            "empleado_id": e["jefe_ops_id"],
            "lineas": [{"product_id": e["product_id"], "cantidad": 90, "costo_unitario": "1.00"}],
        },
        headers=auth_jefe_ops,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["estado"] == "pendiente"


async def test_orden_que_difiere_sin_motivo_es_rechazada(
    client, escenario_compras, auth_jefe_ops, db_session
):
    e = escenario_compras
    await _forzar_sugerencia(db_session, e)
    resp = await client.post(
        "/api/compras/ordenes",
        json={
            "proveedor_id": e["proveedor_id"],
            "tienda_id": e["tienda_id"],
            "empleado_id": e["jefe_ops_id"],
            "lineas": [{"product_id": e["product_id"], "cantidad": 200, "costo_unitario": "1.00"}],
        },
        headers=auth_jefe_ops,
    )
    assert resp.status_code == 422, resp.text


async def test_orden_que_difiere_con_motivo_se_acepta(
    client, escenario_compras, auth_jefe_ops, db_session
):
    e = escenario_compras
    await _forzar_sugerencia(db_session, e)
    resp = await client.post(
        "/api/compras/ordenes",
        json={
            "proveedor_id": e["proveedor_id"],
            "tienda_id": e["tienda_id"],
            "empleado_id": e["jefe_ops_id"],
            "lineas": [{"product_id": e["product_id"], "cantidad": 200, "costo_unitario": "1.00"}],
            "motivo_desviacion": "Promoción de temporada, se anticipa mayor demanda",
        },
        headers=auth_jefe_ops,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["motivo_desviacion"].startswith("Promoción")
    assert len(body["lineas"]) == 1


async def test_aprobar_orden_cambia_estado(client, escenario_compras, auth_jefe_ops, db_session):
    e = escenario_compras
    await _forzar_sugerencia(db_session, e)
    orden = (
        await client.post(
            "/api/compras/ordenes",
            json={
                "proveedor_id": e["proveedor_id"],
                "tienda_id": e["tienda_id"],
                "empleado_id": e["jefe_ops_id"],
                "lineas": [
                    {"product_id": e["product_id"], "cantidad": 90, "costo_unitario": "1.00"}
                ],
            },
            headers=auth_jefe_ops,
        )
    ).json()
    resp = await client.post(
        f"/api/compras/ordenes/{orden['orden_id']}/aprobar", headers=auth_jefe_ops
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "aprobada"


async def _orden_aprobada(client, e, db_session, auth) -> int:
    await _forzar_sugerencia(db_session, e)
    orden = (
        await client.post(
            "/api/compras/ordenes",
            json={
                "proveedor_id": e["proveedor_id"],
                "tienda_id": e["tienda_id"],
                "empleado_id": e["jefe_ops_id"],
                "lineas": [
                    {"product_id": e["product_id"], "cantidad": 90, "costo_unitario": "1.00"}
                ],
            },
            headers=auth,
        )
    ).json()
    oid = orden["orden_id"]
    await client.post(f"/api/compras/ordenes/{oid}/aprobar", headers=auth)
    return oid


async def test_respuesta_proveedor_aceptar_confirma_la_orden(
    client, escenario_compras, auth_jefe_ops, db_session
):
    e = escenario_compras
    orden_id = await _orden_aprobada(client, e, db_session, auth_jefe_ops)
    resp = await client.post(
        f"/api/compras/ordenes/{orden_id}/respuesta-proveedor",
        json={"decision": "aceptar", "canal": "whatsapp", "motivo": "Confirma despacho el jueves"},
        headers=auth_jefe_ops,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["estado"] == "confirmada"
    assert body["proveedor_confirmo"] is True
    assert body["canal_respuesta"] == "whatsapp"
    assert body["respuesta_proveedor"].startswith("Confirma")


async def test_respuesta_proveedor_rechazar_y_motivo_obligatorio(
    client, escenario_compras, auth_jefe_ops, db_session
):
    e = escenario_compras
    orden_id = await _orden_aprobada(client, e, db_session, auth_jefe_ops)
    # motivo vacío → 422
    vacio = await client.post(
        f"/api/compras/ordenes/{orden_id}/respuesta-proveedor",
        json={"decision": "rechazar", "canal": "correo", "motivo": ""},
        headers=auth_jefe_ops,
    )
    assert vacio.status_code == 422, vacio.text

    rech = await client.post(
        f"/api/compras/ordenes/{orden_id}/respuesta-proveedor",
        json={"decision": "rechazar", "canal": "correo", "motivo": "Sin stock hasta marzo"},
        headers=auth_jefe_ops,
    )
    assert rech.status_code == 200, rech.text
    assert rech.json()["estado"] == "rechazada"
    assert rech.json()["proveedor_confirmo"] is False


async def test_proveedores_listado_para_selector(client, escenario_compras, auth_jefe_ops):
    e = escenario_compras
    resp = await client.get("/api/compras/proveedores", headers=auth_jefe_ops)
    assert resp.status_code == 200, resp.text
    ids = {p["proveedor_id"] for p in resp.json()}
    assert e["proveedor_id"] in ids


async def test_listar_y_detalle_ordenes(
    client, escenario_compras, auth_jefe_ops, db_session
):
    e = escenario_compras
    await _forzar_sugerencia(db_session, e)
    resp = await client.post(
        "/api/compras/ordenes",
        json={
            "proveedor_id": e["proveedor_id"],
            "tienda_id": e["tienda_id"],
            "empleado_id": e["jefe_ops_id"],
            "lineas": [{"product_id": e["product_id"], "cantidad": 200, "costo_unitario": "1.00"}],
            "motivo_desviacion": "Stock para evento",
        },
        headers=auth_jefe_ops,
    )
    assert resp.status_code == 201, resp.text
    orden = resp.json()

    # Listar ordenes
    listado = await client.get(
        f"/api/compras/ordenes?tienda_id={e['tienda_id']}", headers=auth_jefe_ops
    )
    assert listado.status_code == 200, listado.text
    items = listado.json()
    assert any(o["orden_id"] == orden["orden_id"] for o in items)

    # Detalle orden
    detalle = await client.get(
        f"/api/compras/ordenes/{orden['orden_id']}", headers=auth_jefe_ops
    )
    assert detalle.status_code == 200, detalle.text
    d = detalle.json()
    assert d["orden_id"] == orden["orden_id"]
    assert len(d["lineas"]) == 1

