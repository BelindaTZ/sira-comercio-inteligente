"""Contrato de la pantalla CRM (feature 002): `GET /clientes/directorio`,
`GET /clientes/resumen-crm`, `GET /clientes/{id}/ficha360`.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def _alta(client, auth, email="crm@example.com"):
    r = await client.post(
        "/api/clientes",
        json={
            "nombre": "Cliente CRM",
            "email": email,
            "documento_identidad": "12.345.678-5",
            "consentimiento_datos": True,
        },
        headers=auth,
    )
    assert r.status_code == 201, r.text
    return r.json()["household_id"]


async def test_directorio_incluye_cliente_nuevo(client, escenario_pos, auth_cajero):
    hid = await _alta(client, auth_cajero)
    r = await client.get("/api/clientes/directorio?size=100", headers=auth_cajero)
    assert r.status_code == 200, r.text
    fila = next(f for f in r.json()["items"] if f["household_id"] == hid)
    # sin ventas todavía: LTV, puntos y frecuencia en cero, sin nivel
    assert fila["ltv"] == "0"
    assert fila["puntos"] == 0
    assert fila["tickets"] == 0
    assert fila["nivel_nombre"] is None


async def test_resumen_crm_trae_kpis_y_niveles(client, escenario_pos, auth_cajero):
    r = await client.get("/api/clientes/resumen-crm", headers=auth_cajero)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("base_activos", "tasa_redencion_pct", "redimidos", "con_clv", "niveles"):
        assert k in d
    assert {n["nombre"] for n in d["niveles"]} == {"Bronce", "Plata", "Oro", "Platino"}


async def test_ficha360_de_cliente_sin_compras(client, escenario_pos, auth_cajero):
    hid = await _alta(client, auth_cajero, email="ficha@example.com")
    r = await client.get(f"/api/clientes/{hid}/ficha360", headers=auth_cajero)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["household_id"] == hid
    assert d["puntos"] == 0
    assert d["valor_canje_clp"] == 0
    assert d["cupones"] == []
    assert d["compras"] == []
