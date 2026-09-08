"""T028 — contrato de clima laboral y su cruce con rotación (feature 011,
`contracts/recursos-humanos.md`, FR-006/FR-007/FR-010).
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_registrar_clima_y_cruce_con_rotacion(
    client, db_session, escenario_rrhh, auth_jefe_rrhh
):
    e = escenario_rrhh

    # una baja dentro de 2026-S2 en la tienda A
    await db_session.execute(
        text(
            "UPDATE empleados SET activo = false, fecha_baja = DATE '2026-09-15' "
            "WHERE empleado_id = :emp"
        ),
        {"emp": e["cajero_a1"]},
    )
    await db_session.flush()

    registro = await client.post(
        "/api/rrhh/clima-laboral",
        json={"tienda_id": e["tienda_a"], "periodo": "2026-S2", "resultado_promedio": 7.5},
        headers=auth_jefe_rrhh,
    )
    assert registro.status_code == 201, registro.text

    cruce = await client.get(
        f"/api/rrhh/tiendas/{e['tienda_a']}/clima-rotacion",
        params={"periodo": "2026-S2"},
        headers=auth_jefe_rrhh,
    )
    assert cruce.status_code == 200, cruce.text
    cuerpo = cruce.json()
    assert float(cuerpo["resultado_promedio"]) == 7.5
    assert cuerpo["tasa_rotacion_pct"] is not None and cuerpo["tasa_rotacion_pct"] > 0


async def test_periodo_sin_encuesta_devuelve_404(client, escenario_rrhh, auth_jefe_rrhh):
    e = escenario_rrhh
    resp = await client.get(
        f"/api/rrhh/tiendas/{e['tienda_a']}/clima-rotacion",
        params={"periodo": "2025-S1"},
        headers=auth_jefe_rrhh,
    )
    assert resp.status_code == 404
