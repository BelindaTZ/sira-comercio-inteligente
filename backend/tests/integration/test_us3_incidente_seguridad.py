"""T029 — integración US3: Escenario 3 de quickstart.md.

Registrar (con y sin datáfono) → transicionar hasta cerrado → conteo del periodo
lo incluye. Un incidente de seguridad y un incidente de fraude (006) sobre el
mismo datáfono coexisten sin relación.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_ciclo_incidente_conteo_e_independencia_del_fraude(
    client, escenario_pagos, auth_caja_ti, auth_caja_finanzas, db_session
):
    e = escenario_pagos

    abrir = await client.post(
        "/api/caja/incidentes-seguridad-pago",
        json={"datafono_id": e["datafono_viejo"], "descripcion": "Posible clonación de tarjetas"},
        headers=auth_caja_ti,
    )
    assert abrir.status_code == 201
    inc = abrir.json()["incidente_seguridad_id"]

    for nuevo in ("en_investigacion", "cerrado"):
        r = await client.patch(
            f"/api/caja/incidentes-seguridad-pago/{inc}/transicionar",
            json={"estado_nuevo": nuevo},
            headers=auth_caja_ti,
        )
        assert r.status_code == 200 and r.json()["estado"] == nuevo

    # incidente sin datáfono (Edge Case)
    generico = await client.post(
        "/api/caja/incidentes-seguridad-pago",
        json={"descripcion": "Reporte del banco sobre varias transacciones"},
        headers=auth_caja_ti,
    )
    assert generico.status_code == 201 and generico.json()["datafono_id"] is None

    hoy = datetime.now(UTC).date()
    conteo = await client.get(
        "/api/caja/incidentes-seguridad-pago/conteo",
        params={
            "desde": (hoy - timedelta(days=1)).isoformat(),
            "hasta": (hoy + timedelta(days=1)).isoformat(),
        },
        headers=auth_caja_finanzas,
    )
    assert conteo.status_code == 200 and conteo.json()["total"] >= 2

    # un incidente_fraude (006) sobre el MISMO datáfono → coexisten sin fusionarse.
    # (incidentes_fraude referencia empleado, no datáfono; el vínculo es sólo
    # conceptual — se comprueba que ambas tablas tienen su propia fila.)
    await db_session.execute(
        text(
            "INSERT INTO incidentes_fraude (empleado_id, descripcion, estado) "
            "VALUES (:emp, 'Fraude interno de caja', 'abierto')"
        ),
        {"emp": e["cajero_id"]},
    )
    await db_session.flush()
    n_seguridad = await db_session.scalar(
        text("SELECT COUNT(*) FROM incidente_seguridad_pago WHERE datafono_id = :d"),
        {"d": e["datafono_viejo"]},
    )
    n_fraude = await db_session.scalar(
        text("SELECT COUNT(*) FROM incidentes_fraude WHERE empleado_id = :e"),
        {"e": e["cajero_id"]},
    )
    assert n_seguridad >= 1 and n_fraude >= 1  # independientes, cada uno en su tabla
