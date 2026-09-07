"""T039 — contrato de campaña de reactivación (FR-016, FR-017).

Una campaña de reactivación NO se puede enviar sin al menos un miembro
`grupo = "control"` — responde 422 (SC-004, requisito duro).
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _clientes(db_session, n) -> list[int]:
    ids = []
    for i in range(n):
        hid = await db_session.scalar(
            text(
                "INSERT INTO clientes (nombre, email, consentimiento_datos, activo) "
                "VALUES (:n, :e, true, true) RETURNING household_id"
            ),
            {"n": f"c{i}", "e": f"react-{i}-{date.today()}@e.com"},
        )
        ids.append(hid)
    await db_session.flush()
    return ids


def _payload(miembros):
    hoy = date.today()
    return {
        "categoria_sira": "reactivacion",
        "start_date": hoy.isoformat(),
        "end_date": (hoy + timedelta(days=30)).isoformat(),
        "miembros": miembros,
    }


async def test_enviar_sin_grupo_control_da_422(
    client, escenario_pos, auth_jefe_marketing, db_session
):
    ids = await _clientes(db_session, 3)
    crea = await client.post(
        "/api/clientes/campanas",
        json=_payload([{"household_id": h, "grupo": "tratado"} for h in ids]),
        headers=auth_jefe_marketing,
    )
    assert crea.status_code == 201, crea.text
    campaign_id = crea.json()["campaign_id"]

    envio = await client.post(
        f"/api/clientes/campanas/{campaign_id}/enviar", headers=auth_jefe_marketing
    )
    assert envio.status_code == 422, envio.text
    assert "control" in envio.json()["error"]["message"].lower()


async def test_con_grupo_control_se_envia(client, escenario_pos, auth_jefe_marketing, db_session):
    # un ancla para que el cupón se pueda emitir
    pid = await db_session.scalar(text("SELECT COALESCE(MAX(product_id), 0) + 1 FROM productos"))
    await db_session.execute(
        text(
            "INSERT INTO productos (product_id, product_category, product_type, costo, "
            "precio_base, es_ancla, activo) VALUES (:p, 'C', 'T', 2.00, 12.00, true, true)"
        ),
        {"p": pid},
    )
    ids = await _clientes(db_session, 4)
    miembros = [
        {"household_id": ids[0], "grupo": "control"},
        {"household_id": ids[1], "grupo": "control"},
    ]
    miembros += [{"household_id": h, "grupo": "tratado"} for h in ids[2:]]

    crea = await client.post(
        "/api/clientes/campanas", json=_payload(miembros), headers=auth_jefe_marketing
    )
    campaign_id = crea.json()["campaign_id"]

    envio = await client.post(
        f"/api/clientes/campanas/{campaign_id}/enviar", headers=auth_jefe_marketing
    )
    assert envio.status_code == 200, envio.text
    assert envio.json()["enviados"] == 2  # sólo el grupo tratado

    # reenviar da 409 (ya enviada)
    reenvio = await client.post(
        f"/api/clientes/campanas/{campaign_id}/enviar", headers=auth_jefe_marketing
    )
    assert reenvio.status_code == 409, reenvio.text


async def test_cliente_sin_consentimiento_no_puede_entrar_a_campana(
    client, escenario_pos, auth_jefe_marketing, db_session
):
    hid = await db_session.scalar(
        text(
            "INSERT INTO clientes (nombre, email, consentimiento_datos, activo) "
            "VALUES ('x', 'sinc@e.com', false, true) RETURNING household_id"
        )
    )
    await db_session.flush()
    resp = await client.post(
        "/api/clientes/campanas",
        json=_payload([{"household_id": hid, "grupo": "tratado"}]),
        headers=auth_jefe_marketing,
    )
    assert resp.status_code == 422, resp.text


async def test_cajero_no_puede_crear_campana(client, escenario_pos, auth_cajero, db_session):
    ids = await _clientes(db_session, 1)
    resp = await client.post(
        "/api/clientes/campanas",
        json=_payload([{"household_id": ids[0], "grupo": "control"}]),
        headers=auth_cajero,
    )
    assert resp.status_code == 403, resp.text
