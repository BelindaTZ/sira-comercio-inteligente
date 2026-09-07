"""T063 — contrato PATCH / DELETE de producto (FR-010, FR-011).

El precio ya aplicado en ventas pasadas (`venta_detalle.sales_value`) no cambia;
la baja es lógica (`activo=false`) y conserva el historial de ventas.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_patch_precio_no_altera_ventas_pasadas(
    client, escenario_pos, auth_cajero, auth_jefe_comercial, db_session
):
    e = escenario_pos
    # Venta confirmada al precio actual (2.50)
    venta = (
        await client.post(
            "/api/ventas",
            json={"tienda_id": e["tienda_id"], "cajero_id": e["cajero_id"]},
            headers=auth_cajero,
        )
    ).json()
    await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas",
        json={"product_id": e["product_id"], "cantidad": 2},
        headers=auth_cajero,
    )
    await client.post(
        f"/api/ventas/{venta['venta_id']}/confirmar",
        json={"medio_pago_id": e["medio_efectivo"]},
        headers=auth_cajero,
    )

    # Cambio de precio en el catálogo
    resp = await client.patch(
        f"/api/catalogo/productos/{e['product_id']}",
        json={"precio_base": "9.99"},
        headers=auth_jefe_comercial,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["precio_base"] == "9.99"

    congelado = await db_session.scalar(
        text("SELECT sales_value FROM venta_detalle WHERE venta_id = :v AND product_id = :p"),
        {"v": venta["venta_id"], "p": e["product_id"]},
    )
    assert str(congelado) == "2.50"  # FR-010: no cambió

    historico = await db_session.scalar(
        text("SELECT COUNT(*) FROM historial_precios WHERE product_id = :p"),
        {"p": e["product_id"]},
    )
    assert historico >= 1  # se conservó el rastro del cambio


async def test_delete_es_baja_logica(client, escenario_pos, auth_jefe_comercial, db_session):
    e = escenario_pos
    resp = await client.delete(
        f"/api/catalogo/productos/{e['product_id']}", headers=auth_jefe_comercial
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["activo"] is False

    # el registro sigue existiendo (FR-011)
    existe = await db_session.scalar(
        text("SELECT COUNT(*) FROM productos WHERE product_id = :p"), {"p": e["product_id"]}
    )
    assert existe == 1


async def test_cajero_no_puede_editar_catalogo(client, escenario_pos, auth_cajero):
    resp = await client.patch(
        f"/api/catalogo/productos/{escenario_pos['product_id']}",
        json={"precio_base": "1.00"},
        headers=auth_cajero,
    )
    assert resp.status_code == 403, resp.text
