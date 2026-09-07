"""T020 — contrato GET / PATCH /api/clientes/niveles-fidelizacion (FR-006, FR-007)."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_listar_niveles(client, escenario_pos, auth_cajero):
    resp = await client.get("/api/clientes/niveles-fidelizacion", headers=auth_cajero)
    assert resp.status_code == 200, resp.text
    nombres = [n["nombre"] for n in resp.json()]
    assert nombres == sorted(
        nombres, key=lambda n: {"Bronce": 0, "Plata": 1, "Oro": 2, "Platino": 3}[n]
    )
    assert "Bronce" in nombres and "Platino" in nombres


async def test_jefe_marketing_ajusta_umbral(client, escenario_pos, auth_jefe_marketing):
    niveles = (
        await client.get("/api/clientes/niveles-fidelizacion", headers=auth_jefe_marketing)
    ).json()
    plata = next(n for n in niveles if n["nombre"] == "Plata")

    resp = await client.patch(
        f"/api/clientes/niveles-fidelizacion/{plata['nivel_id']}",
        json={"umbral_clv_min": "0.35"},
        headers=auth_jefe_marketing,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["umbral_clv_min"] == "0.35"


async def test_cajero_no_puede_ajustar_umbral(client, escenario_pos, auth_cajero):
    resp = await client.patch(
        "/api/clientes/niveles-fidelizacion/1",
        json={"umbral_clv_min": "0.5"},
        headers=auth_cajero,
    )
    assert resp.status_code == 403, resp.text


async def test_ajustar_nivel_inexistente_da_404(client, escenario_pos, auth_jefe_marketing):
    resp = await client.patch(
        "/api/clientes/niveles-fidelizacion/99999",
        json={"umbral_clv_min": "0.5"},
        headers=auth_jefe_marketing,
    )
    assert resp.status_code == 404
