"""Contrato de la pantalla de Riesgo de Fuga (feature 013): resumen de cohorte,
directorio enriquecido, export y segmentos para campaña de reactivación.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _alta(client, auth, email) -> int:
    return (
        await client.post(
            "/api/clientes",
            json={"nombre": email, "email": email, "consentimiento_datos": True},
            headers=auth,
        )
    ).json()["household_id"]


async def _compras(db_session, e, household_id, dias_atras) -> None:
    for d in dias_atras:
        vid = await db_session.scalar(
            text(
                "INSERT INTO ventas (tienda_id, cajero_id, household_id, fecha_hora, semana, "
                "total, estado) VALUES (:t, :c, :h, :f, 1, 5, 'confirmada') RETURNING venta_id"
            ),
            {"t": e["tienda_id"], "c": e["cajero_id"], "h": household_id,
             "f": date.today() - timedelta(days=d)},
        )
        await db_session.execute(
            text("INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
                 "VALUES (:v, :p, 1, 5)"),
            {"v": vid, "p": e["product_id"]},
        )
    await db_session.flush()


@pytest.fixture
async def _cohorte(client, escenario_pos, auth_cajero, db_session):
    e = escenario_pos
    riesgo = await _alta(client, auth_cajero, "rf-riesgo@e.com")
    inactivo = await _alta(client, auth_cajero, "rf-inactivo@e.com")
    inactivo2 = await _alta(client, auth_cajero, "rf-inactivo2@e.com")
    await _compras(db_session, e, riesgo, [60, 50, 40, 30, 20])
    await _compras(db_session, e, inactivo, [110, 100, 90, 80, 70])
    await _compras(db_session, e, inactivo2, [120, 108, 96, 84, 72])
    await client.post("/api/_dev/jobs/clv_churn_semanal")
    return {"riesgo": riesgo, "inactivo": inactivo, "inactivo2": inactivo2}


async def test_resumen_de_cohorte(client, _cohorte, auth_jefe_marketing):
    r = await client.get("/api/clientes/riesgo-fuga/resumen", headers=auth_jefe_marketing)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["clientes_riesgo"] >= 2
    assert "ltv_en_riesgo" in d
    assert isinstance(d["categorias_afectadas"], list)


async def test_directorio_enriquecido(client, _cohorte, auth_jefe_marketing):
    r = await client.get(
        "/api/clientes/riesgo-fuga/directorio?size=50", headers=auth_jefe_marketing
    )
    assert r.status_code == 200, r.text
    fila = next(f for f in r.json()["items"] if f["household_id"] == _cohorte["inactivo"])
    assert fila["severidad"] == "inactivo"
    assert fila["dias_desde_ultima_compra"] is not None
    assert "ltv" in fila and "frecuencia_sem" in fila


async def test_export_cohorte_xlsx(client, _cohorte, auth_jefe_marketing):
    r = await client.get(
        "/api/clientes/riesgo-fuga/export?formato=xlsx", headers=auth_jefe_marketing
    )
    assert r.status_code == 200, r.text
    assert "spreadsheetml" in r.headers["content-type"]
    assert len(r.content) > 100


async def test_segmentos_riesgo_y_campana_por_segmento(
    client, _cohorte, auth_jefe_marketing
):
    segs = await client.get("/api/clientes/segmentos-riesgo", headers=auth_jefe_marketing)
    assert segs.status_code == 200, segs.text
    claves = {s["clave"] for s in segs.json()}
    assert "riesgo_alto_general" in claves

    r = await client.post(
        "/api/clientes/campanas",
        json={
            "nombre": "Reactivación por segmento",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=30)),
            "segmento": "riesgo_alto_general",
        },
        headers=auth_jefe_marketing,
    )
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["nombre"] == "Reactivación por segmento"
    grupos = {m["grupo"] for m in d["miembros"]}
    assert grupos == {"tratado", "control"}  # split automático


async def test_cajero_no_ve_el_directorio_de_riesgo(client, escenario_pos, auth_cajero):
    r = await client.get("/api/clientes/riesgo-fuga/directorio", headers=auth_cajero)
    assert r.status_code == 403
