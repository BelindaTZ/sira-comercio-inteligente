"""T041 — integración US5: Escenario 7 de quickstart.md (FR-016..FR-019, SC-004).

Campaña de reactivación con grupo de control obligatorio; al cierre el uplift
compara la tasa de retorno de tratado vs control (no la redención del cupón).
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _ancla(db_session) -> int:
    pid = await db_session.scalar(text("SELECT COALESCE(MAX(product_id), 0) + 1 FROM productos"))
    await db_session.execute(
        text(
            "INSERT INTO productos (product_id, product_category, product_type, costo, "
            "precio_base, es_ancla, activo) VALUES (:p, 'C', 'T', 2.00, 12.00, true, true)"
        ),
        {"p": pid},
    )
    return pid


async def _clientes(db_session, n, prefijo) -> list[int]:
    ids = []
    for i in range(n):
        hid = await db_session.scalar(
            text(
                "INSERT INTO clientes (nombre, email, consentimiento_datos, activo) "
                "VALUES (:n, :e, true, true) RETURNING household_id"
            ),
            {"n": f"{prefijo}{i}", "e": f"{prefijo}{i}-{date.today()}@e.com"},
        )
        ids.append(hid)
    await db_session.flush()
    return ids


async def _compra(db_session, e, household_id) -> None:
    # posterior al envío en reloj de BD (NOW() del servidor, no hora local).
    vid = await db_session.scalar(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, household_id, fecha_hora, semana, "
            "total, estado) VALUES (:t, :c, :h, NOW() + INTERVAL '1 hour', 1, 10, 'confirmada') "
            "RETURNING venta_id"
        ),
        {"t": e["tienda_id"], "c": e["cajero_id"], "h": household_id},
    )
    await db_session.execute(
        text(
            "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
            "VALUES (:v, :p, 1, 10)"
        ),
        {"v": vid, "p": e["product_id"]},
    )
    await db_session.flush()


async def test_escenario_7_uplift_con_grupo_de_control(
    client, escenario_pos, auth_jefe_marketing, db_session
):
    e = escenario_pos
    await _ancla(db_session)
    tratados = await _clientes(db_session, 5, "trat")
    controles = await _clientes(db_session, 5, "ctrl")
    hoy = date.today()

    # 1-2: crear con TODOS como tratado y verificar que enviar da 422.
    solo_tratado = {
        "categoria_sira": "reactivacion",
        "start_date": hoy.isoformat(),
        "end_date": (hoy + timedelta(days=30)).isoformat(),
        "miembros": [{"household_id": h, "grupo": "tratado"} for h in tratados + controles],
    }
    c1 = await client.post("/api/clientes/campanas", json=solo_tratado, headers=auth_jefe_marketing)
    assert (
        await client.post(
            f"/api/clientes/campanas/{c1.json()['campaign_id']}/enviar", headers=auth_jefe_marketing
        )
    ).status_code == 422

    # 4: recrear con 5 tratado / 5 control y enviar → 200.
    miembros = [{"household_id": h, "grupo": "tratado"} for h in tratados]
    miembros += [{"household_id": h, "grupo": "control"} for h in controles]
    crea = await client.post(
        "/api/clientes/campanas",
        json={**solo_tratado, "miembros": miembros},
        headers=auth_jefe_marketing,
    )
    campaign_id = crea.json()["campaign_id"]
    envio = await client.post(
        f"/api/clientes/campanas/{campaign_id}/enviar", headers=auth_jefe_marketing
    )
    assert envio.status_code == 200 and envio.json()["enviados"] == 5

    # 5: 4 de 5 tratados vuelven a comprar; sólo 1 de 5 controles.
    for h in tratados[:4]:
        await _compra(db_session, e, h)
    await _compra(db_session, e, controles[0])

    # 6-7: cerrar y verificar uplift = 0.8 - 0.2 = 0.6.
    cierre = await client.post(
        f"/api/clientes/campanas/{campaign_id}/cerrar", headers=auth_jefe_marketing
    )
    assert cierre.status_code == 200, cierre.text
    res = cierre.json()["resultado"]
    assert res["tasa_retorno_tratado"] == "0.8000"
    assert res["tasa_retorno_control"] == "0.2000"
    assert res["uplift"] == "0.6000"

    # cerrar dos veces → 409
    assert (
        await client.post(
            f"/api/clientes/campanas/{campaign_id}/cerrar", headers=auth_jefe_marketing
        )
    ).status_code == 409

    # 8: decisión de escalar.
    dec = await client.post(
        f"/api/clientes/campanas/{campaign_id}/decision",
        json={"decision": "aprobada_escalar"},
        headers=auth_jefe_marketing,
    )
    assert dec.status_code == 200, dec.text
    assert dec.json()["resultado"]["decision"] == "aprobada_escalar"


async def test_decision_requiere_campana_cerrada(
    client, escenario_pos, auth_jefe_marketing, db_session
):
    await _ancla(db_session)
    ids = await _clientes(db_session, 2, "d")
    hoy = date.today()
    crea = await client.post(
        "/api/clientes/campanas",
        json={
            "categoria_sira": "reactivacion",
            "start_date": hoy.isoformat(),
            "end_date": (hoy + timedelta(days=10)).isoformat(),
            "miembros": [
                {"household_id": ids[0], "grupo": "tratado"},
                {"household_id": ids[1], "grupo": "control"},
            ],
        },
        headers=auth_jefe_marketing,
    )
    resp = await client.post(
        f"/api/clientes/campanas/{crea.json()['campaign_id']}/decision",
        json={"decision": "descartada"},
        headers=auth_jefe_marketing,
    )
    assert resp.status_code == 422, resp.text
