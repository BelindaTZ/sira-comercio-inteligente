"""T062 — contrato POST /api/catalogo/productos (FR-009, FR-012, FR-013).

El autocompletado vía Open Food Facts se mockea; lo que se verifica es que el
alta funciona con o sin coincidencia y que exige la clasificación ancla/nicho.
"""

import pytest
from src.integrations.openfoodfacts_client import ProductoExterno
from src.modules.catalogo import service as catalogo_service

pytestmark = pytest.mark.asyncio


async def test_alta_con_autocompletado(client, escenario_pos, auth_jefe_comercial, monkeypatch):
    async def _fake(barcode):  # noqa: ARG001
        return ProductoExterno(
            nombre="Jugo de Naranja 1L",
            marca="Marca X",
            categoria="Jugos",
            imagen_url="http://x/img.png",
        )

    monkeypatch.setattr(catalogo_service.openfoodfacts_client, "buscar_por_barcode", _fake)

    resp = await client.post(
        "/api/catalogo/productos",
        json={
            "codigo_barras": "7790001112223",
            "costo": "1.10",
            "precio_base": "1.99",
            "es_perecedero": True,
            "clasificacion": "nicho",
        },
        headers=auth_jefe_comercial,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["nombre"] == "Jugo de Naranja 1L"
    assert body["product_category"] == "Jugos"
    assert body["es_ancla"] is False
    assert body["autocompletado"] is True
    assert body["product_id"] >= 90_000_000  # generador de altas nuevas


async def test_alta_sin_coincidencia_no_bloquea(
    client, escenario_pos, auth_jefe_comercial, monkeypatch
):
    async def _sin_match(barcode):  # noqa: ARG001
        return None

    monkeypatch.setattr(catalogo_service.openfoodfacts_client, "buscar_por_barcode", _sin_match)

    resp = await client.post(
        "/api/catalogo/productos",
        json={
            "codigo_barras": "0000000000001",
            "nombre": "Producto Manual",
            "categoria": "Varios",
            "costo": "2.00",
            "precio_base": "3.50",
            "es_perecedero": False,
            "clasificacion": "ancla",
        },
        headers=auth_jefe_comercial,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["nombre"] == "Producto Manual"
    assert body["es_ancla"] is True
    assert body["autocompletado"] is False


async def test_codigo_barras_duplicado_da_409(
    client, escenario_pos, auth_jefe_comercial, db_session
):
    resp = await client.post(
        "/api/catalogo/productos",
        json={
            "codigo_barras": escenario_pos["codigo_barras"],  # ya existe (escenario_pos)
            "nombre": "Duplicado",
            "categoria": "X",
            "costo": "1.00",
            "precio_base": "1.00",
            "es_perecedero": False,
            "clasificacion": "nicho",
        },
        headers=auth_jefe_comercial,
    )
    assert resp.status_code == 409, resp.text


async def test_clasificacion_es_obligatoria(client, escenario_pos, auth_jefe_comercial):
    resp = await client.post(
        "/api/catalogo/productos",
        json={
            "codigo_barras": "111",
            "costo": "1.00",
            "precio_base": "1.00",
            "es_perecedero": False,
        },
        headers=auth_jefe_comercial,
    )
    assert resp.status_code == 422  # falta 'clasificacion'
