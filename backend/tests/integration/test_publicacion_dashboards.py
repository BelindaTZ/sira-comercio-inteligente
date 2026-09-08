"""Integration tests — publicación y lectura de dashboards multinivel (feature 009).

Cubre T013/T014 (US1), T020/T021 (US2) y T028 (US3) contra quickstart.md, con
fixtures que simulan el resultado del job diario (sin ClickHouse/Airflow reales).
"""

import pytest

pytestmark = pytest.mark.asyncio

BASE = "/api"


async def _forzar(client, headers, tipo, **body):
    return await client.post(
        f"{BASE}/ti/dashboards/{tipo}/forzar-publicacion", json=body or None, headers=headers
    )


# ================================================================ US1
async def test_oe4_no_disponible_oe8_con_valor_real(
    client, escenario_dashboards, auth_dash_ti, auth_gerente_general
):
    """T013 — OE-4 (Market Share/NPS) siempre no disponible; OE-8 (fuente 011)
    con valor real (Acceptance Scenario 2, corrección de esta ronda)."""
    await _forzar(client, auth_dash_ti, "estrategico")
    resp = await client.get(f"{BASE}/direccion/dashboard-estrategico", headers=auth_gerente_general)
    kpis = {k["dimension"]: k for k in resp.json()["kpis"]}

    assert kpis["OE-4"]["disponible"] is False
    assert kpis["OE-4"]["valor"] is None

    assert kpis["OE-8"]["disponible"] is True
    assert float(kpis["OE-8"]["valor"]) == pytest.approx(8.0)  # AVG(7.5, 8.5) del fixture


async def test_endpoint_siempre_devuelve_la_publicacion_mas_reciente(
    client, escenario_dashboards, auth_dash_ti, auth_gerente_general
):
    """T014 — dos publicaciones sucesivas: el endpoint devuelve la más nueva."""
    p1 = (await _forzar(client, auth_dash_ti, "estrategico")).json()["publicacion_id"]
    p2 = (await _forzar(client, auth_dash_ti, "estrategico")).json()["publicacion_id"]
    assert p2 != p1

    resp = await client.get(f"{BASE}/direccion/dashboard-estrategico", headers=auth_gerente_general)
    assert resp.json()["publicacion_id"] == max(p1, p2)


# ================================================================ US2
async def test_aislamiento_entre_jefes_y_acceso_del_gerente(
    client, escenario_dashboards, auth_dash_ti, auth_dash_comercial, auth_gerente_general
):
    """T020 — un Jefe_Comercial no lee Finanzas (403); Gerente_General sí (200)."""
    await _forzar(client, auth_dash_ti, "tactico")  # publica los 6 módulos

    propio = await client.get(
        f"{BASE}/ti/dashboards/tactico/Comercial", headers=auth_dash_comercial
    )
    assert propio.status_code == 200, propio.text

    ajeno = await client.get(f"{BASE}/ti/dashboards/tactico/Finanzas", headers=auth_dash_comercial)
    assert ajeno.status_code == 403

    gerente = await client.get(
        f"{BASE}/ti/dashboards/tactico/Finanzas", headers=auth_gerente_general
    )
    assert gerente.status_code == 200, gerente.text


async def test_kpi_no_disponible_no_bloquea_el_resto(
    client, escenario_dashboards, auth_dash_ti, auth_dash_comercial
):
    """T021 — un KPI `disponible: false` por datos insuficientes convive con los
    KPIs que sí tienen valor en el mismo dashboard (Acceptance Scenario 3)."""
    await _forzar(client, auth_dash_ti, "tactico", modulo_nombre="Comercial")
    resp = await client.get(f"{BASE}/ti/dashboards/tactico/Comercial", headers=auth_dash_comercial)
    kpis = resp.json()["kpis"]
    assert any(k["disponible"] is False and k["valor"] is None for k in kpis)
    assert any(k["disponible"] is True for k in kpis)


# ================================================================ US3
async def test_dashboard_operativo_desactualizado_aparece_señalado(
    client, escenario_dashboards, auth_dash_ti
):
    """T028 — `seguimiento_merma` del fixture tiene > 1 día de antigüedad: aparece
    como no disponible en la verificación y en las alertas (Acceptance Scenario 2)."""
    tienda_id = escenario_dashboards["tienda_id"]
    await _forzar(client, auth_dash_ti, "operativo")

    verif = await client.get(f"{BASE}/ti/dashboards/operativos/verificacion", headers=auth_dash_ti)
    por_dashboard = {
        f["nombre_dashboard"]: f
        for f in verif.json()["estado_por_tienda"]
        if f["tienda_id"] == tienda_id
    }
    assert por_dashboard["seguimiento_merma"]["disponible"] is False
    assert por_dashboard["alertas_reposicion"]["disponible"] is True
    assert por_dashboard["cuadre_caja"]["disponible"] is True

    alertas = await client.get(f"{BASE}/ti/dashboards/operativos/alertas", headers=auth_dash_ti)
    nombres_alertados = {
        f["nombre_dashboard"]
        for f in alertas.json()["estado_por_tienda"]
        if f["tienda_id"] == tienda_id
    }
    assert "seguimiento_merma" in nombres_alertados
    assert "alertas_reposicion" not in nombres_alertados
