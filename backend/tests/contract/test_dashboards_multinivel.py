"""Contract tests — Dashboards Multinivel (feature 009).

Cubre T012 (US1), T019 (US2), T026/T027 (US3) y FR-010 contra
`contracts/dashboards-multinivel.md`. Base path real: `/api` (ronda 1 — el
contrato decía `/api/v1`, mismo criterio que 010/012).

Los escenarios que dependen de un snapshot ya publicado lo generan con el trigger
manual de FR-010 (`POST /ti/dashboards/{tipo}/forzar-publicacion`) — no requieren
ClickHouse/Airflow reales (quickstart.md).
"""

import pytest

pytestmark = pytest.mark.asyncio

BASE = "/api"


async def _forzar(client, headers, tipo, **body):
    return await client.post(
        f"{BASE}/ti/dashboards/{tipo}/forzar-publicacion", json=body or None, headers=headers
    )


# ------------------------------------------------------------------ US1: estratégico
async def test_dashboard_estrategico_200_con_kpis_y_fecha(
    client, escenario_dashboards, auth_dash_ti, auth_gerente_general
):
    forzar = await _forzar(client, auth_dash_ti, "estrategico")
    assert forzar.status_code == 202, forzar.text
    assert forzar.json()["estado"] == "en_proceso"

    resp = await client.get(f"{BASE}/direccion/dashboard-estrategico", headers=auth_gerente_general)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["publicacion_id"] > 0
    assert cuerpo["fecha_publicacion"]
    dims = {k["dimension"] for k in cuerpo["kpis"]}
    assert {"OE-1", "OE-4", "OE-8"} <= dims


async def test_dashboard_estrategico_sin_publicacion_404(
    client, escenario_dashboards, auth_gerente_general
):
    resp = await client.get(f"{BASE}/direccion/dashboard-estrategico", headers=auth_gerente_general)
    assert resp.status_code == 404


async def test_dashboard_estrategico_rbac_403_cajero(client, escenario_dashboards, auth_cajero):
    resp = await client.get(f"{BASE}/direccion/dashboard-estrategico", headers=auth_cajero)
    assert resp.status_code == 403


# ------------------------------------------------------------------ US2: táctico
async def test_dashboard_tactico_200_filtrado_a_su_dimension(
    client, escenario_dashboards, auth_dash_ti, auth_dash_comercial
):
    forzar = await _forzar(client, auth_dash_ti, "tactico", modulo_nombre="Comercial")
    assert forzar.status_code == 202, forzar.text

    resp = await client.get(f"{BASE}/ti/dashboards/tactico/Comercial", headers=auth_dash_comercial)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["kpis"], "el dashboard táctico debe traer KPIs"
    assert all(k["dimension"] == "Comercial" for k in cuerpo["kpis"])


async def test_dashboard_tactico_modulo_desconocido_404(
    client, escenario_dashboards, auth_gerente_general
):
    resp = await client.get(f"{BASE}/ti/dashboards/tactico/NoExiste", headers=auth_gerente_general)
    assert resp.status_code == 404


async def test_dashboard_tactico_sin_publicacion_404(
    client, escenario_dashboards, auth_dash_comercial
):
    resp = await client.get(f"{BASE}/ti/dashboards/tactico/Comercial", headers=auth_dash_comercial)
    assert resp.status_code == 404


# ------------------------------------------------------------------ US3: verificación operativa
async def test_verificacion_operativos_200(client, escenario_dashboards, auth_dash_ti):
    forzar = await _forzar(client, auth_dash_ti, "operativo")
    assert forzar.status_code == 202, forzar.text

    resp = await client.get(f"{BASE}/ti/dashboards/operativos/verificacion", headers=auth_dash_ti)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["publicacion_id"] > 0
    filas = cuerpo["estado_por_tienda"]
    assert filas
    campos = {"tienda_id", "nombre_dashboard", "fecha_ultima_actualizacion", "disponible"}
    for f in filas:
        assert campos <= f.keys()


async def test_alertas_operativos_solo_no_disponibles(client, escenario_dashboards, auth_dash_ti):
    await _forzar(client, auth_dash_ti, "operativo")
    resp = await client.get(f"{BASE}/ti/dashboards/operativos/alertas", headers=auth_dash_ti)
    assert resp.status_code == 200, resp.text
    filas = resp.json()["estado_por_tienda"]
    assert all(f["disponible"] is False for f in filas)


async def test_verificacion_operativos_rbac_403_cajero(client, escenario_dashboards, auth_cajero):
    resp = await client.get(f"{BASE}/ti/dashboards/operativos/verificacion", headers=auth_cajero)
    assert resp.status_code == 403


# ------------------------------------------------------------------ FR-010: forzar publicación
async def test_forzar_publicacion_rbac_403_cajero(client, escenario_dashboards, auth_cajero):
    resp = await _forzar(client, auth_cajero, "estrategico")
    assert resp.status_code == 403
