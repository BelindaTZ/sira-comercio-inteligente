"""T025 — integración US3 (feature 011): Escenario 3 de quickstart.md.

Registrar clima → verificar cruce con la rotación calculada del mismo periodo →
un periodo sin encuesta devuelve 404 (sin dato inventado, FR-010).
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_clima_cruzado_con_rotacion(client, db_session, escenario_rrhh, auth_jefe_rrhh):
    e = escenario_rrhh

    # 1 de 3 empleados-cajero de la tienda A causa baja en el 2º semestre de 2026
    await db_session.execute(
        text(
            "UPDATE empleados SET activo = false, fecha_baja = DATE '2026-08-01' "
            "WHERE empleado_id = :e"
        ),
        {"e": e["cajero_a1"]},
    )
    await db_session.flush()

    assert (
        await client.post(
            "/api/rrhh/clima-laboral",
            json={"tienda_id": e["tienda_a"], "periodo": "2026-S2", "resultado_promedio": 6.8},
            headers=auth_jefe_rrhh,
        )
    ).status_code == 201

    cruce = await client.get(
        f"/api/rrhh/tiendas/{e['tienda_a']}/clima-rotacion",
        params={"periodo": "2026-S2"},
        headers=auth_jefe_rrhh,
    )
    assert cruce.status_code == 200
    cuerpo = cruce.json()
    assert float(cuerpo["resultado_promedio"]) == 6.8
    assert cuerpo["tasa_rotacion_pct"] is not None

    sin_encuesta = await client.get(
        f"/api/rrhh/tiendas/{e['tienda_a']}/clima-rotacion",
        params={"periodo": "2026-S1"},
        headers=auth_jefe_rrhh,
    )
    assert sin_encuesta.status_code == 404
