"""T034 — integración US4: Escenario 5 de quickstart.md (FR-012, FR-013, SC-003).

Un cliente activo cuyo cumpleaños es hoy recibe su evento + cupón sin
intervención manual; un cliente dado de baja NO. La redención se refleja en la
tasa por hito.
"""

from datetime import date

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _cliente(db_session, email, *, nace_hoy=True, activo=True, consent=True) -> int:
    hoy = date.today()
    fn = date(1985, hoy.month, hoy.day) if nace_hoy else date(1985, 1, 1)
    # `fecha_registro` fija en el pasado: aísla el hito de cumpleaños del de
    # aniversario de registro (que también dispara cupón).
    return await db_session.scalar(
        text(
            "INSERT INTO clientes (nombre, email, fecha_nacimiento, fecha_registro, "
            "consentimiento_datos, activo) VALUES (:n, :e, :fn, DATE '2020-02-15', :c, :a) "
            "RETURNING household_id"
        ),
        {"n": email, "e": email, "fn": fn, "c": consent, "a": activo},
    )


async def _producto_ancla(db_session, *, costo, precio) -> int:
    pid = await db_session.scalar(text("SELECT COALESCE(MAX(product_id), 0) + 1 FROM productos"))
    await db_session.execute(
        text(
            "INSERT INTO productos (product_id, product_category, product_type, costo, "
            "precio_base, es_ancla, activo) VALUES (:p, 'C', 'T', :co, :pr, true, true)"
        ),
        {"p": pid, "co": costo, "pr": precio},
    )
    return pid


async def test_escenario_5_cupon_automatico_de_cumpleanos(
    client, escenario_pos, auth_cajero, auth_jefe_marketing, db_session
):
    # dos anclas: el cupón sale sobre el de mayor margen (precio - costo).
    await _producto_ancla(db_session, costo=8.00, precio=10.00)  # margen 2
    ancla_top = await _producto_ancla(db_session, costo=3.00, precio=15.00)  # margen 12 ← gana

    cumple = await _cliente(db_session, "cumple@e.com")
    baja = await _cliente(db_session, "baja@e.com", activo=False)
    sin_consent = await _cliente(db_session, "sinconsent@e.com", consent=False)
    otro_dia = await _cliente(db_session, "otrodia@e.com", nace_hoy=False)
    await db_session.flush()

    job = await client.post("/api/_dev/jobs/eventos_hito_diario")
    assert job.status_code == 200, job.text
    assert job.json() == {"eventos_generados": 1, "cupones_enviados": 1}

    # correr de nuevo no duplica (idempotente).
    assert (await client.post("/api/_dev/jobs/eventos_hito_diario")).json()[
        "eventos_generados"
    ] == 0

    eventos = (
        await client.get(f"/api/clientes/{cumple}/eventos", headers=auth_jefe_marketing)
    ).json()
    assert len(eventos) == 1
    assert eventos[0]["tipo_evento"] == "cumpleanos"
    assert eventos[0]["cupon_enviado"] is not None
    assert eventos[0]["redimido"] is False

    for hid in (baja, sin_consent, otro_dia):
        assert (
            await client.get(f"/api/clientes/{hid}/eventos", headers=auth_jefe_marketing)
        ).json() == []

    # el cupón salió sobre el ancla de mayor margen.
    upc = eventos[0]["cupon_enviado"]
    prod_cupon = await db_session.scalar(
        text("SELECT product_id FROM cupones WHERE coupon_upc = :u"), {"u": upc}
    )
    assert prod_cupon == ancla_top

    campaign_id = await db_session.scalar(
        text("SELECT campaign_id FROM campanas WHERE categoria_sira = 'hito' LIMIT 1")
    )
    red = await client.post(
        f"/api/clientes/cupones/{upc}/redimir",
        json={"household_id": cumple, "campaign_id": campaign_id},
        headers=auth_cajero,
    )
    assert red.status_code == 201, red.text

    tasa = (
        await client.get(
            "/api/clientes/cupones/tasa-redencion?tipo_evento=cumpleanos",
            headers=auth_jefe_marketing,
        )
    ).json()
    fila = next(f for f in tasa if f["tipo_evento"] == "cumpleanos")
    assert fila["enviados"] == 1 and fila["redimidos"] == 1
    assert fila["tasa"] == 1.0

    eventos_post = (
        await client.get(f"/api/clientes/{cumple}/eventos", headers=auth_jefe_marketing)
    ).json()
    assert eventos_post[0]["redimido"] is True


async def test_aniversario_de_registro_tambien_dispara_cupon(
    client, escenario_pos, auth_jefe_marketing, db_session
):
    await _producto_ancla(db_session, costo=3.00, precio=15.00)
    hoy = date.today()
    hid = await db_session.scalar(
        text(
            "INSERT INTO clientes (nombre, email, fecha_nacimiento, fecha_registro, "
            "consentimiento_datos, activo) VALUES ('Ani', 'ani@e.com', DATE '1985-02-15', "
            ":fr, true, true) RETURNING household_id"
        ),
        {"fr": date(2023, hoy.month, hoy.day)},
    )
    await db_session.flush()

    job = await client.post("/api/_dev/jobs/eventos_hito_diario")
    assert job.json()["eventos_generados"] == 1

    eventos = (await client.get(f"/api/clientes/{hid}/eventos", headers=auth_jefe_marketing)).json()
    assert eventos[0]["tipo_evento"] == "aniversario_registro"
    assert eventos[0]["cupon_enviado"] is not None
