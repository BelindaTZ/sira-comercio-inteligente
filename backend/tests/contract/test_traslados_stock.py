"""Contract tests — Traslados de Stock entre Tiendas (feature 012).

Cubre T010, T011 (US1), T018-T020 (US2), T030-T032 (US3) de tasks.md contra
`contracts/traslados-stock-entre-tiendas.md`.
"""

import pytest

pytestmark = pytest.mark.asyncio


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------ US1
async def test_disponibilidad_sucursales_200(client, escenario_traslados, auth_traslados_ops):
    e = escenario_traslados
    resp = await client.get(
        f"/api/traslados/productos/{e['product_id']}/disponibilidad-sucursales",
        headers=auth_traslados_ops,
    )
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["product_id"] == e["product_id"]
    por_tienda = {d["tienda_id"]: d["cantidad_disponible"] for d in cuerpo["disponibilidad"]}
    assert por_tienda[e["tienda_a"]] == 200
    assert por_tienda[e["tienda_b"]] == 10


async def test_disponibilidad_producto_inexistente_404(
    client, escenario_traslados, auth_traslados_ops
):
    resp = await client.get(
        "/api/traslados/productos/99999999/disponibilidad-sucursales", headers=auth_traslados_ops
    )
    assert resp.status_code == 404


async def test_sugerencias_incluye_disponibilidad_otras_tiendas(
    client, escenario_traslados, auth_traslados_ops
):
    e = escenario_traslados
    # tienda B está bajo su punto de reposición para el producto del escenario
    resp = await client.get(
        "/api/compras/sugerencias", params={"tienda_id": e["tienda_b"]}, headers=auth_traslados_ops
    )
    assert resp.status_code == 200, resp.text
    sugerencia = next(s for s in resp.json() if s["product_id"] == e["product_id"])
    assert "disponibilidad_otras_tiendas" in sugerencia
    otras = {
        d["tienda_id"]: d["cantidad_disponible"] for d in sugerencia["disponibilidad_otras_tiendas"]
    }
    assert otras.get(e["tienda_a"]) == 200
    assert e["tienda_b"] not in otras  # la propia tienda no se incluye


# ------------------------------------------------------------------ US2
async def test_post_traslado_201_y_validaciones_422(client, escenario_traslados):
    e = escenario_traslados
    ok = await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_b"],
            "cantidad": 10,
        },
        headers=_bearer(e["token_encargado_b"]),
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["estado"] == "solicitado"

    misma_tienda = await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_a"],
            "cantidad": 5,
        },
        headers=_bearer(e["token_encargado_a"]),
    )
    assert misma_tienda.status_code == 422

    cantidad_cero = await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_b"],
            "cantidad": 0,
        },
        headers=_bearer(e["token_encargado_b"]),
    )
    assert cantidad_cero.status_code == 422


async def test_listar_traslados_encargado_limitado_a_su_tienda_origen(client, escenario_traslados):
    e = escenario_traslados
    await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_b"],
            "cantidad": 3,
        },
        headers=_bearer(e["token_encargado_b"]),
    )
    # el Encargado de A ve la solicitud (su tienda es la origen)
    vista_a = await client.get(
        "/api/traslados", params={"estado": "solicitado"}, headers=_bearer(e["token_encargado_a"])
    )
    assert vista_a.status_code == 200
    assert all(t["tienda_origen_id"] == e["tienda_a"] for t in vista_a.json())
    assert len(vista_a.json()) >= 1

    # el Encargado de A no puede pedir el listado de otra tienda origen
    forzado = await client.get(
        "/api/traslados",
        params={"tienda_origen_id": e["tienda_b"]},
        headers=_bearer(e["token_encargado_a"]),
    )
    assert forzado.status_code == 403


async def test_resolucion_aprobar_rechazar_y_409_por_exceso(client, escenario_traslados):
    e = escenario_traslados

    async def _solicitar(cantidad: int) -> int:
        r = await client.post(
            "/api/traslados",
            json={
                "product_id": e["product_id"],
                "tienda_origen_id": e["tienda_a"],
                "tienda_destino_id": e["tienda_b"],
                "cantidad": cantidad,
            },
            headers=_bearer(e["token_encargado_b"]),
        )
        assert r.status_code == 201
        return r.json()["traslado_id"]

    aprobar_id = await _solicitar(20)
    aprob = await client.patch(
        f"/api/traslados/{aprobar_id}/resolucion",
        json={"decision": "aprobar"},
        headers=_bearer(e["token_encargado_a"]),
    )
    assert aprob.status_code == 200, aprob.text
    assert aprob.json()["estado"] == "en_transito"
    assert aprob.json()["resuelto_por"] == e["encargado_a_id"]
    assert aprob.json()["fecha_resolucion"] is not None

    rechazar_id = await _solicitar(5)
    rech = await client.patch(
        f"/api/traslados/{rechazar_id}/resolucion",
        json={"decision": "rechazar", "motivo": "stock reservado"},
        headers=_bearer(e["token_encargado_a"]),
    )
    assert rech.status_code == 200 and rech.json()["estado"] == "rechazado"

    exceso_id = await _solicitar(100000)
    exceso = await client.patch(
        f"/api/traslados/{exceso_id}/resolucion",
        json={"decision": "aprobar"},
        headers=_bearer(e["token_encargado_a"]),
    )
    assert exceso.status_code == 409, exceso.text
    assert exceso.json()["error"]["details"]["stock_disponible"] >= 0


async def test_encargado_destino_no_puede_resolver(client, escenario_traslados):
    e = escenario_traslados
    r = await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_b"],
            "cantidad": 3,
        },
        headers=_bearer(e["token_encargado_b"]),
    )
    traslado_id = r.json()["traslado_id"]
    resp = await client.patch(
        f"/api/traslados/{traslado_id}/resolucion",
        json={"decision": "aprobar"},
        headers=_bearer(e["token_encargado_b"]),
    )
    assert resp.status_code == 403


# ------------------------------------------------------------------ US3
async def _traslado_en_transito(client, e) -> int:
    r = await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_b"],
            "cantidad": 15,
        },
        headers=_bearer(e["token_encargado_b"]),
    )
    tid = r.json()["traslado_id"]
    await client.patch(
        f"/api/traslados/{tid}/resolucion",
        json={"decision": "aprobar"},
        headers=_bearer(e["token_encargado_a"]),
    )
    return tid


async def test_recepcion_200_y_409_si_no_esta_en_transito(client, escenario_traslados):
    e = escenario_traslados
    tid = await _traslado_en_transito(client, e)

    rec = await client.patch(
        f"/api/traslados/{tid}/recepcion", headers=_bearer(e["token_encargado_b"])
    )
    assert rec.status_code == 200, rec.text
    assert rec.json()["estado"] == "recibido"
    assert rec.json()["recibido_por"] == e["encargado_b_id"]

    # repetir: ya no está en_transito
    otra = await client.patch(
        f"/api/traslados/{tid}/recepcion", headers=_bearer(e["token_encargado_b"])
    )
    assert otra.status_code == 409


async def test_cancelacion_200_y_409_si_ya_no_esta_solicitado(client, escenario_traslados):
    e = escenario_traslados
    r = await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_b"],
            "cantidad": 4,
        },
        headers=_bearer(e["token_encargado_b"]),
    )
    tid = r.json()["traslado_id"]

    canc = await client.patch(
        f"/api/traslados/{tid}/cancelacion", headers=_bearer(e["token_encargado_b"])
    )
    assert canc.status_code == 200 and canc.json()["estado"] == "cancelado"

    de_nuevo = await client.patch(
        f"/api/traslados/{tid}/cancelacion", headers=_bearer(e["token_encargado_b"])
    )
    assert de_nuevo.status_code == 409


async def test_reporte_semanal_marca_pendiente_confirmacion(client, escenario_traslados):
    e = escenario_traslados
    tid = await _traslado_en_transito(client, e)

    from datetime import date, timedelta

    hoy = date.today()
    resp = await client.get(
        "/api/traslados/reporte-semanal",
        params={
            "desde": (hoy - timedelta(days=1)).isoformat(),
            "hasta": (hoy + timedelta(days=1)).isoformat(),
        },
        headers=_bearer(e["token_ops"]),
    )
    assert resp.status_code == 200, resp.text
    fila = next(t for t in resp.json() if t["traslado_id"] == tid)
    assert fila["pendiente_confirmacion"] is True


# ------------------------------------------------------------------ feature 018
async def test_listar_tiendas_para_selectores(client, escenario_traslados):
    e = escenario_traslados
    resp = await client.get("/api/traslados/tiendas", headers=_bearer(e["token_encargado_a"]))
    assert resp.status_code == 200, resp.text
    por_id = {t["tienda_id"]: t for t in resp.json()}
    assert e["tienda_a"] in por_id and e["tienda_b"] in por_id
    assert por_id[e["tienda_a"]]["nombre"] == "Traslados A"


async def test_listado_trae_nombres_no_solo_ids(client, escenario_traslados):
    e = escenario_traslados
    await client.post(
        "/api/traslados",
        json={
            "product_id": e["product_id"],
            "tienda_origen_id": e["tienda_a"],
            "tienda_destino_id": e["tienda_b"],
            "cantidad": 3,
        },
        headers=_bearer(e["token_encargado_b"]),
    )
    resp = await client.get(
        "/api/traslados", params={"estado": "solicitado"}, headers=_bearer(e["token_encargado_a"])
    )
    assert resp.status_code == 200, resp.text
    fila = resp.json()[0]
    assert fila["tienda_origen_nombre"] == "Traslados A"
    assert fila["tienda_destino_nombre"] == "Traslados B"
    assert "producto_nombre" in fila  # el producto del escenario no tiene nombre seteado
    assert fila["solicitante_nombre"] is not None


async def test_encargado_destino_ve_entrantes_con_direccion_destino(client, escenario_traslados):
    e = escenario_traslados
    tid = await _traslado_en_transito(client, e)
    resp = await client.get(
        "/api/traslados",
        params={"direccion": "destino", "estado": "en_transito"},
        headers=_bearer(e["token_encargado_b"]),
    )
    assert resp.status_code == 200, resp.text
    ids = {t["traslado_id"] for t in resp.json()}
    assert tid in ids
    assert all(t["tienda_destino_id"] == e["tienda_b"] for t in resp.json())
