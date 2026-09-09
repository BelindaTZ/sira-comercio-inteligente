"""Contrato de gestión de precios y márgenes (001, US4):
`GET /catalogo/precios` (matriz con estado de margen), `GET /catalogo/resumen`
(snapshot de KPIs) y `POST /catalogo/productos/{id}/simular-precio`.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_matriz_precios_trae_estado_de_margen(client, escenario_pos, auth_jefe_comercial):
    r = await client.get("/api/catalogo/precios?size=5", headers=auth_jefe_comercial)
    assert r.status_code == 200, r.text
    fila = next(f for f in r.json()["items"] if f["product_id"] == escenario_pos["product_id"])
    assert fila["estado_margen"] in {"optimo", "ajustado", "bajo", "sin_precio"}
    # producto de escenario_pos: costo 1.00 / precio 2.50 → margen 60%
    assert fila["margen_pct"] == pytest.approx(60.0, abs=0.1)


async def test_matriz_precios_filtra_por_id_de_producto(client, escenario_pos, auth_jefe_comercial):
    pid = escenario_pos["product_id"]
    r = await client.get(f"/api/catalogo/precios?search={pid}", headers=auth_jefe_comercial)
    assert r.status_code == 200, r.text
    ids = {f["product_id"] for f in r.json()["items"]}
    assert pid in ids


async def test_resumen_catalogo_calcula_en_vivo_si_no_hay_snapshot(
    client, escenario_pos, auth_jefe_comercial
):
    r = await client.get("/api/catalogo/resumen", headers=auth_jefe_comercial)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("total_activos", "con_ean", "skus_bajo_margen", "margen_bruto_ponderado_pct"):
        assert k in d
    assert d["total_activos"] >= 1


async def test_refrescar_kpi_job_persiste_el_snapshot(db_session, escenario_pos):
    from sqlalchemy import text
    from src.jobs import refrescar_catalogo_kpi_job

    await refrescar_catalogo_kpi_job.ejecutar(db_session)
    ts = await db_session.scalar(text("SELECT calculado_at FROM catalogo_kpi WHERE id = 1"))
    assert ts is not None


async def test_export_precios_en_los_tres_formatos(client, escenario_pos, auth_jefe_comercial):
    for fmt, ct in [
        ("csv", "text/csv"),
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("pdf", "application/pdf"),
    ]:
        r = await client.get(
            f"/api/catalogo/precios/export?formato={fmt}", headers=auth_jefe_comercial
        )
        assert r.status_code == 200, r.text
        assert ct in r.headers["content-type"]
        assert r.headers["content-disposition"].endswith(f'.{fmt}"')
        assert len(r.content) > 100
    bad = await client.get("/api/catalogo/precios/export?formato=word", headers=auth_jefe_comercial)
    assert bad.status_code == 422


async def test_simular_precio_sube_margen_al_subir_pvp(client, escenario_pos, auth_jefe_comercial):
    r = await client.post(
        f"/api/catalogo/productos/{escenario_pos['product_id']}/simular-precio",
        json={"delta_pct": "6"},
        headers=auth_jefe_comercial,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert float(d["pvp_nuevo"]) > float(d["pvp_actual"])
    assert d["margen_nuevo_pct"] > d["margen_actual_pct"]
    assert "factor_elasticidad" in d

    # fuera del rango permitido (Field ge=-30, le=30)
    fuera = await client.post(
        f"/api/catalogo/productos/{escenario_pos['product_id']}/simular-precio",
        json={"delta_pct": "80"},
        headers=auth_jefe_comercial,
    )
    assert fuera.status_code == 422
