"""T038 — integración US4: Escenario 5 de quickstart.md.

Consultar protocolo vigente → aplicar sobre un incidente abierto → cerrar con
resultado, sin acusar al empleado si no se confirma. El ciclo funciona igual con
un empleado que ya tiene `fecha_baja` (FR-016).
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _incidente_ciclo_completo(client, e, auth_fin, auth_enc, empleado_id):
    abrir = await client.post(
        "/api/caja/incidentes-fraude",
        json={"empleado_id": empleado_id, "descripcion": "Patrón sospechoso"},
        headers=auth_fin,
    )
    assert abrir.status_code == 201, abrir.text
    inc = abrir.json()["incidente_id"]

    aplicar = await client.patch(
        f"/api/caja/incidentes-fraude/{inc}/aplicar-protocolo",
        json={"acciones_tomadas": "Entrevista + arqueo sorpresa"},
        headers=auth_enc,
    )
    assert aplicar.status_code == 200, aplicar.text
    assert aplicar.json()["estado"] == "en_revision"

    cerrar = await client.patch(
        f"/api/caja/incidentes-fraude/{inc}/cerrar",
        json={"resultado": "descartado"},
        headers=auth_fin,
    )
    assert cerrar.status_code == 200, cerrar.text
    assert cerrar.json()["estado"] == "cerrado"
    assert cerrar.json()["resultado"] == "descartado"  # sin acusar al empleado
    return inc


async def test_ciclo_incidente_y_empleado_dado_de_baja(
    client, escenario_caja, auth_caja_finanzas, auth_encargado, db_session
):
    e = escenario_caja

    definir = await client.put(
        "/api/caja/protocolo-escalamiento",
        json={"texto": "1) Documentar. 2) Escalar a Finanzas. 3) Cerrar con resultado."},
        headers=auth_caja_finanzas,
    )
    assert definir.status_code == 201, definir.text

    protocolo = await client.get("/api/caja/protocolo-escalamiento", headers=auth_encargado)
    assert protocolo.status_code == 200
    assert "Documentar" in protocolo.json()["texto"]

    # incidente sobre el cajero activo
    await _incidente_ciclo_completo(
        client, e, auth_caja_finanzas, auth_encargado, e["cajero_id"]
    )

    # empleado dado de baja: el ciclo no se bloquea (FR-016)
    puesto_id = await db_session.scalar(
        text("SELECT puesto_id FROM empleados WHERE empleado_id = :e"), {"e": e["cajero_id"]}
    )
    baja_id = await db_session.scalar(
        text(
            "INSERT INTO empleados (tienda_id, puesto_id, nombre, fecha_contratacion, "
            "fecha_baja, activo) VALUES (:t, :p, 'Ex Cajero', CURRENT_DATE, CURRENT_DATE, false) "
            "RETURNING empleado_id"
        ),
        {"t": e["tienda_id"], "p": puesto_id},
    )
    await db_session.flush()

    await _incidente_ciclo_completo(
        client, e, auth_caja_finanzas, auth_encargado, baja_id
    )
