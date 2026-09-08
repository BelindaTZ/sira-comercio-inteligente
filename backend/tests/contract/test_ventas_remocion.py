"""T017 — contrato DELETE /api/ventas/{id}/lineas/{id} (FR-027, SC-007).

403 si quien autoriza es el mismo cajero de la venta; 200 y registro en
`lineas_venta_removidas` si es un empleado distinto (el Encargado_Tienda).
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _venta_con_linea(client, escenario_pos, auth_cajero):
    venta = (
        await client.post(
            "/api/ventas",
            json={
                "tienda_id": escenario_pos["tienda_id"],
                "cajero_id": escenario_pos["cajero_id"],
            },
            headers=auth_cajero,
        )
    ).json()
    venta = (
        await client.post(
            f"/api/ventas/{venta['venta_id']}/lineas",
            json={"product_id": escenario_pos["product_id"], "cantidad": 2},
            headers=auth_cajero,
        )
    ).json()
    return venta


async def test_remover_linea_autorizada_por_el_cajero_devuelve_403(
    client, escenario_pos, auth_cajero
):
    venta = await _venta_con_linea(client, escenario_pos, auth_cajero)
    linea_id = venta["lineas"][0]["venta_detalle_id"]

    resp = await client.request(
        "DELETE",
        f"/api/ventas/{venta['venta_id']}/lineas/{linea_id}",
        json={"autoriza_empleado_id": escenario_pos["cajero_id"], "motivo": "error de escaneo"},
        headers=auth_cajero,
    )
    assert resp.status_code == 403, resp.text


async def test_remover_linea_nombrando_a_un_tercero_ausente_devuelve_403(
    client, escenario_pos, auth_cajero
):
    """checklists/security.md:12 (T073) — doble persona entre requests separados:
    el cajero autenticado no puede nombrar a otro empleado como autorizador si ese
    empleado no firma el request con su propio JWT."""
    venta = await _venta_con_linea(client, escenario_pos, auth_cajero)
    linea_id = venta["lineas"][0]["venta_detalle_id"]

    resp = await client.request(
        "DELETE",
        f"/api/ventas/{venta['venta_id']}/lineas/{linea_id}",
        json={
            "autoriza_empleado_id": escenario_pos["encargado_id"],  # un empleado real, pero ausente
            "motivo": "intento de auto-autorización en dos pasos",
        },
        headers=auth_cajero,  # el cajero, no el encargado
    )
    assert resp.status_code == 403, resp.text


async def test_remover_linea_autorizada_por_encargado_devuelve_200_y_audita(
    client, escenario_pos, auth_encargado, db_session
):
    venta = await _venta_con_linea(
        client, escenario_pos, {"Authorization": auth_encargado["Authorization"]}
    )
    linea_id = venta["lineas"][0]["venta_detalle_id"]

    resp = await client.request(
        "DELETE",
        f"/api/ventas/{venta['venta_id']}/lineas/{linea_id}",
        json={
            "autoriza_empleado_id": escenario_pos["encargado_id"],
            "motivo": "cliente se arrepiente",
        },
        headers=auth_encargado,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["lineas"] == []

    registrada = await db_session.scalar(
        text(
            "SELECT COUNT(*) FROM lineas_venta_removidas "
            "WHERE venta_id = :v AND autoriza_empleado_id = :e"
        ),
        {"v": venta["venta_id"], "e": escenario_pos["encargado_id"]},
    )
    assert registrada == 1
