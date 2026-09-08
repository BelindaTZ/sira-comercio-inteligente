"""Contrato de cuentas de usuario y administración de RBAC (FR-007, FR-008,
FR-012, FR-013)."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_crear_cuenta_y_rechazo_de_duplicada(
    client, escenario_auth, auth_admin_ti, db_session
):
    e = escenario_auth
    emp = await db_session.scalar(
        text(
            "INSERT INTO empleados (tienda_id, puesto_id, nombre, fecha_contratacion) "
            "VALUES (:t, :p, 'Empleado sin cuenta', CURRENT_DATE) RETURNING empleado_id"
        ),
        {"t": e["tienda_id"], "p": e["puesto_id"]},
    )
    await db_session.flush()

    crear = await client.post(
        "/api/sistema/usuarios",
        json={
            "empleado_id": emp,
            "username": "nuevo.usuario",
            "password_inicial": "Inicial-2026-abc",
            "role_id": e["rol_cajero_id"],
        },
        headers=auth_admin_ti,
    )
    assert crear.status_code == 201, crear.text
    assert crear.json()["activo"] is True

    dup = await client.post(
        "/api/sistema/usuarios",
        json={
            "empleado_id": emp,
            "username": "otro.nombre",
            "password_inicial": "Inicial-2026-abc",
            "role_id": e["rol_cajero_id"],
        },
        headers=auth_admin_ti,
    )
    assert dup.status_code == 409, dup.text


async def test_asignar_rol_con_efecto_inmediato(client, escenario_auth, auth_admin_ti):
    e = escenario_auth
    # el cajero no puede ver la administración de usuarios
    antes = await client.get(
        f"/api/sistema/usuarios/{e['ti']['usuario_id']}",
        headers={"Authorization": f"Bearer {e['cajero']['token']}"},
    )
    assert antes.status_code == 403

    cambio = await client.patch(
        f"/api/sistema/usuarios/{e['cajero']['usuario_id']}/rol",
        json={"role_id": e["rol_encargado_id"]},
        headers=auth_admin_ti,
    )
    assert cambio.status_code == 200 and cambio.json()["role_id"] == e["rol_encargado_id"]

    # sin nuevo login, el mismo token del cajero ya actúa como Encargado_Tienda
    despues = await client.get(
        "/api/caja/protocolo-escalamiento",
        headers={"Authorization": f"Bearer {e['cajero']['token']}"},
    )
    assert despues.status_code in (200, 404)  # 404 sólo si no hay protocolo; nunca 403


async def test_permisos_modulo_y_tabla(client, escenario_auth, auth_admin_ti, db_session):
    rol_rrhh = await db_session.scalar(text("SELECT role_id FROM roles WHERE nombre = 'Jefe_RRHH'"))
    mod_comercial = await db_session.scalar(
        text("SELECT modulo_id FROM modulos WHERE nombre = 'Comercial'")
    )

    lista = await client.get(
        f"/api/sistema/roles/{rol_rrhh}/permisos-modulo", headers=auth_admin_ti
    )
    assert lista.status_code == 200 and any(m["nombre"] == "Comercial" for m in lista.json())

    # tabla sin acceso al módulo → 409
    sin_modulo = await client.put(
        f"/api/sistema/roles/{rol_rrhh}/permisos-tabla/{mod_comercial}/productos",
        json={"can_select": True},
        headers=auth_admin_ti,
    )
    assert sin_modulo.status_code == 409, sin_modulo.text

    # otorgar módulo, luego tabla
    otorgar = await client.put(
        f"/api/sistema/roles/{rol_rrhh}/permisos-modulo/{mod_comercial}",
        json={"puede_ver": True, "puede_editar": True},
        headers=auth_admin_ti,
    )
    assert otorgar.status_code == 200 and otorgar.json()["puede_ver"] is True

    tabla = await client.put(
        f"/api/sistema/roles/{rol_rrhh}/permisos-tabla/{mod_comercial}/productos",
        json={"can_select": True, "can_update": True},
        headers=auth_admin_ti,
    )
    assert tabla.status_code == 200 and tabla.json()["can_update"] is True


async def test_solo_jefe_ti_administra_sistema(client, escenario_auth):
    e = escenario_auth
    resp = await client.get(
        f"/api/sistema/usuarios/{e['ti']['usuario_id']}",
        headers={"Authorization": f"Bearer {e['rrhh']['token']}"},
    )
    assert resp.status_code == 403
