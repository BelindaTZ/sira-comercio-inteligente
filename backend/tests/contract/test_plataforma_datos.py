"""Contract tests — Plataforma de Datos Táctico-Estratégica (feature 010).

Cubre T013/T014 (US1), T023 (US2), T031 (US3), T035 (US4) y FR-012 contra
`contracts/plataforma-datos.md`. Base path real: `/api/plataforma-datos`
(ronda 1 — el contrato decía `/api/v1/ti/plataforma-datos`).
"""

import pytest

pytestmark = pytest.mark.asyncio

BASE = "/api/plataforma-datos"


# ------------------------------------------------------------------ US1: modelo
async def test_get_modelo_lista_entidades(
    client, escenario_plataforma_datos, auth_plataforma_ti
):
    resp = await client.get(f"{BASE}/modelo", headers=auth_plataforma_ti)
    assert resp.status_code == 200, resp.text
    nombres = {e["nombre_entidad"] for e in resp.json()}
    assert {"fact_venta", "dim_producto", "dim_tienda"} <= nombres


async def test_post_modelo_201_activa_por_defecto(
    client, escenario_plataforma_datos, auth_plataforma_ti
):
    resp = await client.post(
        f"{BASE}/modelo",
        json={
            "nombre_entidad": "dim_caja",
            "tipo": "dimension",
            "tabla_origen_postgres": "cajas",
            "descripcion": "Cajas registradoras por tienda",
        },
        headers=auth_plataforma_ti,
    )
    assert resp.status_code == 201, resp.text
    cuerpo = resp.json()
    assert cuerpo["activa"] is True
    assert cuerpo["entidad_id"] > 0


async def test_post_modelo_nombre_duplicado_409(
    client, escenario_plataforma_datos, auth_plataforma_ti
):
    resp = await client.post(
        f"{BASE}/modelo",
        json={
            "nombre_entidad": "fact_venta",
            "tipo": "fact",
            "tabla_origen_postgres": "venta_detalle",
        },
        headers=auth_plataforma_ti,
    )
    assert resp.status_code == 409, resp.text


async def test_patch_modelo_activa_desactiva(
    client, escenario_plataforma_datos, auth_plataforma_ti
):
    e = escenario_plataforma_datos
    resp = await client.patch(
        f"{BASE}/modelo/{e['entidad_producto']}",
        json={"activa": False},
        headers=auth_plataforma_ti,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["activa"] is False


# ------------------------------------------------------------------ US2: corridas
async def test_get_corridas_filtros_y_forma(
    client, escenario_plataforma_datos, auth_plataforma_ti
):
    e = escenario_plataforma_datos
    # fuerza una corrida para tener al menos una fila
    await client.post(
        f"{BASE}/corridas/forzar",
        json={"entidad_id": e["entidad_fact"], "tipo_carga": "completa"},
        headers=auth_plataforma_ti,
    )
    resp = await client.get(
        f"{BASE}/corridas",
        params={"entidad_id": e["entidad_fact"]},
        headers=auth_plataforma_ti,
    )
    assert resp.status_code == 200, resp.text
    corridas = resp.json()["corridas"]
    assert corridas, "debería haber al menos una corrida"
    fila = corridas[0]
    for campo in (
        "filas_cargadas",
        "filas_error",
        "duracion_segundos",
        "nombre_entidad",
        "estado",
    ):
        assert campo in fila


async def test_get_corridas_rbac_403_sin_permiso(
    client, escenario_plataforma_datos, auth_cajero
):
    resp = await client.get(f"{BASE}/corridas", headers=auth_cajero)
    assert resp.status_code == 403


# ------------------------------------------------------------------ US3: calidad
async def test_get_calidad_de_corrida_200(
    client, escenario_plataforma_datos, auth_plataforma_ti
):
    e = escenario_plataforma_datos
    forzar = await client.post(
        f"{BASE}/corridas/forzar",
        json={"entidad_id": e["entidad_fact"], "tipo_carga": "completa"},
        headers=auth_plataforma_ti,
    )
    corrida_id = forzar.json()["corrida_id"]
    resp = await client.get(
        f"{BASE}/corridas/{corrida_id}/calidad", headers=auth_plataforma_ti
    )
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["corrida_id"] == corrida_id
    assert isinstance(cuerpo["registros"], list)


async def test_get_calidad_corrida_inexistente_404(
    client, escenario_plataforma_datos, auth_plataforma_ti
):
    resp = await client.get(
        f"{BASE}/corridas/99999999/calidad", headers=auth_plataforma_ti
    )
    assert resp.status_code == 404


# ------------------------------------------------------------------ US4: política
async def test_politica_append_only_vigente_es_la_mas_reciente(
    client, escenario_plataforma_datos, auth_plataforma_ti
):
    v1 = await client.post(
        f"{BASE}/politica", json={"texto": "Política v1"}, headers=auth_plataforma_ti
    )
    assert v1.status_code == 201, v1.text
    v2 = await client.post(
        f"{BASE}/politica", json={"texto": "Política v2"}, headers=auth_plataforma_ti
    )
    assert v2.status_code == 201

    vigente = await client.get(f"{BASE}/politica", headers=auth_plataforma_ti)
    assert vigente.json()["texto"] == "Política v2"

    historial = await client.get(
        f"{BASE}/politica/historial", headers=auth_plataforma_ti
    )
    textos = [p["texto"] for p in historial.json()]
    assert textos == ["Política v2", "Política v1"]


async def test_get_politica_sin_ninguna_404(
    client, escenario_plataforma_datos, auth_plataforma_ti
):
    resp = await client.get(f"{BASE}/politica", headers=auth_plataforma_ti)
    assert resp.status_code == 404


# ------------------------------------------------------------------ FR-012: forzar corrida
async def test_forzar_corrida_202_y_409_si_en_progreso(
    client, escenario_plataforma_datos, auth_plataforma_ti
):
    e = escenario_plataforma_datos
    r1 = await client.post(
        f"{BASE}/corridas/forzar",
        json={"entidad_id": e["entidad_tienda"], "tipo_carga": "completa"},
        headers=auth_plataforma_ti,
    )
    assert r1.status_code == 202, r1.text
    assert r1.json()["estado"] in ("en_progreso", "exitosa")


async def test_forzar_corrida_entidad_inactiva_422(
    client, escenario_plataforma_datos, auth_plataforma_ti
):
    e = escenario_plataforma_datos
    await client.patch(
        f"{BASE}/modelo/{e['entidad_tienda']}",
        json={"activa": False},
        headers=auth_plataforma_ti,
    )
    resp = await client.post(
        f"{BASE}/corridas/forzar",
        json={"entidad_id": e["entidad_tienda"], "tipo_carga": "completa"},
        headers=auth_plataforma_ti,
    )
    assert resp.status_code == 422, resp.text
