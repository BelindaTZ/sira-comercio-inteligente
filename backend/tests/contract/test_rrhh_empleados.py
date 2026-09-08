"""Contrato de empleados (FR-005, FR-006, FR-014)."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_alta_actualizacion_y_baja_con_cuenta_inhabilitada(
    client, escenario_auth, auth_rrhh, auth_admin_ti
):
    e = escenario_auth

    alta = await client.post(
        "/api/rrhh/empleados",
        json={
            "nombre": "Nuevo Empleado",
            "puesto_id": e["puesto_id"],
            "tienda_id": e["tienda_id"],
            "email": "nuevo.empleado@sira.test",
            "fecha_contratacion": "2026-09-01",
        },
        headers=auth_rrhh,
    )
    assert alta.status_code == 201, alta.text
    emp_id = alta.json()["empleado_id"]
    assert alta.json()["activo"] is True

    patch = await client.patch(
        f"/api/rrhh/empleados/{emp_id}",
        json={"telefono": "099-999-9999"},
        headers=auth_rrhh,
    )
    assert patch.status_code == 200 and patch.json()["telefono"] == "099-999-9999"

    # cuenta para ese empleado
    cuenta = await client.post(
        "/api/sistema/usuarios",
        json={
            "empleado_id": emp_id,
            "username": "nuevo.empleado",
            "password_inicial": "Clave-Inicial-2026",
            "role_id": e["rol_cajero_id"],
        },
        headers=auth_admin_ti,
    )
    usuario_id = cuenta.json()["usuario_id"]

    baja = await client.patch(
        f"/api/rrhh/empleados/{emp_id}/baja",
        json={"fecha_baja": "2026-09-30"},
        headers=auth_rrhh,
    )
    assert baja.status_code == 200 and baja.json()["activo"] is False

    # sin ninguna llamada adicional, el trigger inhabilitó la cuenta
    estado_cuenta = await client.get(
        f"/api/sistema/usuarios/{usuario_id}", headers=auth_admin_ti
    )
    assert estado_cuenta.json()["activo"] is False

    login = await client.post(
        "/api/auth/login",
        json={"username": "nuevo.empleado", "password": "Clave-Inicial-2026"},
    )
    assert login.status_code == 401


async def test_cajero_no_administra_empleados(client, escenario_auth):
    e = escenario_auth
    resp = await client.post(
        "/api/rrhh/empleados",
        json={"nombre": "X", "puesto_id": e["puesto_id"], "fecha_contratacion": "2026-01-01"},
        headers={"Authorization": f"Bearer {e['cajero']['token']}"},
    )
    assert resp.status_code == 403
