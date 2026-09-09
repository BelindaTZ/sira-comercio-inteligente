"""Contract test — GET /api/auth/me (feature 013, shell de navegación).

Devuelve la identidad de la sesión + los módulos que el rol puede ver, para que
el frontend pinte la navegación según el rol (Principio XII). 401 sin token.
"""

import pytest
from sqlalchemy import text
from tests.conftest import _token

pytestmark = pytest.mark.asyncio


async def test_me_devuelve_rol_y_modulos_visibles(client, escenario_auth):
    r = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {escenario_auth['ti']['token']}"}
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["rol"] == "Jefe_TI"
    assert cuerpo["usuario_id"] == escenario_auth["ti"]["usuario_id"]
    assert cuerpo["empleado_id"] == escenario_auth["ti"]["empleado_id"]
    assert cuerpo["username"] == escenario_auth["ti"]["username"]
    assert cuerpo["nombre"]  # nombre del empleado, para el menú de usuario
    nombres = {m["nombre"] for m in cuerpo["modulos"]}
    assert "TI" in nombres  # Jefe_TI ve su módulo
    assert all(m["puede_ver"] for m in cuerpo["modulos"])  # sólo módulos visibles
    # tablas legibles: permiso de tabla (más fino que el de módulo) para filtrar la nav
    tablas = cuerpo["tablas"]
    assert all(t["can_select"] for t in tablas)
    assert any(t["modulo"] == "TI" for t in tablas)


async def test_me_gerente_general_ve_todos_los_modulos(client, escenario_pos, db_session):
    role_id = await db_session.scalar(
        text("SELECT role_id FROM roles WHERE nombre = 'Gerente_General'")
    )
    token = await _token(db_session, role_id=role_id, tienda_id=escenario_pos["tienda_id"])
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    nombres = {m["nombre"] for m in cuerpo["modulos"]}
    # el seed le da puede_ver global en los 9 módulos
    assert {"Direccion", "Comercial", "Finanzas", "TI", "RRHH", "Sistema"} <= nombres
    # feature 018: la sub-barra de contexto necesita el nombre de la sucursal
    assert cuerpo["tienda_id"] == escenario_pos["tienda_id"]
    assert cuerpo["tienda_nombre"] == "Tienda Test"
    # feature 013 / migración 0027: lectura sobre las tablas operativas, sin escritura
    tablas = {(t["modulo"], t["nombre_tabla"]) for t in cuerpo["tablas"]}
    assert ("Comercial", "productos") in tablas
    assert ("Marketing_CRM", "clientes") in tablas
    assert all(not t["can_editar"] for t in cuerpo["tablas"])


async def test_me_cajero_no_ve_sistema_ni_direccion(client, escenario_auth):
    r = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {escenario_auth['cajero']['token']}"},
    )
    assert r.status_code == 200, r.text
    nombres = {m["nombre"] for m in r.json()["modulos"]}
    assert "Sistema" not in nombres
    assert "Direccion" not in nombres
    # el Cajero no puede leer `productos` aunque tenga visible el módulo Comercial
    tablas = {(t["modulo"], t["nombre_tabla"]) for t in r.json()["tablas"]}
    assert ("Comercial", "productos") not in tablas


async def test_me_sin_token_401(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401
