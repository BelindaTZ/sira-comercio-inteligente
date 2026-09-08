"""T032 — integración US4: Escenario 4 de quickstart.md.

Cambio de rol con efecto inmediato (sin nuevo login); ajuste de permiso de tabla
sin acceso previo al módulo → rechazado.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_cambio_de_rol_inmediato_y_permiso_tabla_sin_modulo(
    client, escenario_auth, auth_admin_ti, db_session
):
    e = escenario_auth
    cajero = e["cajero"]

    # el cajero no administra RRHH
    antes = await client.post(
        "/api/rrhh/empleados",
        json={"nombre": "X", "puesto_id": e["puesto_id"], "fecha_contratacion": "2026-01-01"},
        headers={"Authorization": f"Bearer {cajero['token']}"},
    )
    assert antes.status_code == 403

    rol_rrhh = await db_session.scalar(text("SELECT role_id FROM roles WHERE nombre = 'Jefe_RRHH'"))
    cambio = await client.patch(
        f"/api/sistema/usuarios/{cajero['usuario_id']}/rol",
        json={"role_id": rol_rrhh},
        headers=auth_admin_ti,
    )
    assert cambio.status_code == 200

    # el MISMO token del cajero ya actúa como Jefe_RRHH — sin nuevo login
    despues = await client.post(
        "/api/rrhh/empleados",
        json={
            "nombre": "Creado tras cambio de rol",
            "puesto_id": e["puesto_id"],
            "fecha_contratacion": "2026-01-01",
        },
        headers={"Authorization": f"Bearer {cajero['token']}"},
    )
    assert despues.status_code == 201, despues.text

    # permiso de tabla sin acceso al módulo → 409
    mod_direccion = await db_session.scalar(
        text("SELECT modulo_id FROM modulos WHERE nombre = 'Direccion'")
    )
    sin_modulo = await client.put(
        f"/api/sistema/roles/{rol_rrhh}/permisos-tabla/{mod_direccion}/kpis",
        json={"can_select": True},
        headers=auth_admin_ti,
    )
    assert sin_modulo.status_code == 409
