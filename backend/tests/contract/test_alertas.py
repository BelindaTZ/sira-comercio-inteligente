"""T045 — contrato POST /api/inventario/alertas/{id}/atender (FR-021).

Atender una alerta no deja una segunda alerta activa del mismo tipo/producto/tienda
mientras la primera exista; tras atenderla, el job puede volver a generar una.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _crear_alerta_reposicion(db_session, e) -> int:
    return await db_session.scalar(
        text(
            "INSERT INTO alertas_inventario (tipo, product_id, tienda_id, estado) "
            "VALUES ('reposicion', :p, :t, 'pendiente') RETURNING alerta_id"
        ),
        {"p": e["product_id"], "t": e["tienda_id"]},
    )


async def test_atender_alerta_marca_atendida(client, escenario_pos, auth_encargado, db_session):
    e = escenario_pos
    alerta_id = await _crear_alerta_reposicion(db_session, e)
    await db_session.flush()

    resp = await client.post(
        f"/api/inventario/alertas/{alerta_id}/atender",
        json={"empleado_id": e["encargado_id"]},
        headers=auth_encargado,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["estado"] == "atendida"
    assert body["empleado_atiende_id"] == e["encargado_id"]


async def test_no_se_puede_atender_dos_veces(client, escenario_pos, auth_encargado, db_session):
    e = escenario_pos
    alerta_id = await _crear_alerta_reposicion(db_session, e)
    await db_session.flush()
    await client.post(
        f"/api/inventario/alertas/{alerta_id}/atender",
        json={"empleado_id": e["encargado_id"]},
        headers=auth_encargado,
    )
    resp = await client.post(
        f"/api/inventario/alertas/{alerta_id}/atender",
        json={"empleado_id": e["encargado_id"]},
        headers=auth_encargado,
    )
    assert resp.status_code == 422


async def test_indice_unico_parcial_impide_segunda_alerta_activa(client, escenario_pos, db_session):
    e = escenario_pos
    await _crear_alerta_reposicion(db_session, e)
    await db_session.flush()
    with pytest.raises(Exception):  # noqa: B017 - viola el índice único parcial de BD
        await _crear_alerta_reposicion(db_session, e)
        await db_session.flush()


async def test_listar_alertas_filtra_por_estado(client, escenario_pos, auth_encargado, db_session):
    e = escenario_pos
    await _crear_alerta_reposicion(db_session, e)
    await db_session.flush()
    resp = await client.get(
        "/api/inventario/alertas",
        params={"tienda_id": e["tienda_id"], "estado": "pendiente"},
        headers=auth_encargado,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
