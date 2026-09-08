"""T019 — integración US2: Escenario 2 de quickstart.md.

Alta de empleado (Jefe_RRHH) → alta de cuenta (Jefe_TI) → login con el rol
asignado → segunda cuenta para el mismo empleado rechazada.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_alta_empleado_cuenta_y_login(client, escenario_auth, auth_rrhh, auth_admin_ti):
    e = escenario_auth

    empleado = await client.post(
        "/api/rrhh/empleados",
        json={
            "nombre": "Ana Torres",
            "puesto_id": e["puesto_id"],
            "tienda_id": e["tienda_id"],
            "email": "ana.torres@sira.test",
            "fecha_contratacion": "2026-09-01",
        },
        headers=auth_rrhh,
    )
    assert empleado.status_code == 201
    emp_id = empleado.json()["empleado_id"]

    cuenta = await client.post(
        "/api/sistema/usuarios",
        json={
            "empleado_id": emp_id,
            "username": "ana.torres",
            "password_inicial": "Bienvenida-2026",
            "role_id": e["rol_encargado_id"],
        },
        headers=auth_admin_ti,
    )
    assert cuenta.status_code == 201

    login = await client.post(
        "/api/auth/login", json={"username": "ana.torres", "password": "Bienvenida-2026"}
    )
    assert login.status_code == 200

    dup = await client.post(
        "/api/sistema/usuarios",
        json={
            "empleado_id": emp_id,
            "username": "ana.otra",
            "password_inicial": "Bienvenida-2026",
            "role_id": e["rol_cajero_id"],
        },
        headers=auth_admin_ti,
    )
    assert dup.status_code == 409
