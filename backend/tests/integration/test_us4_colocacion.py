"""T039 — integración US4: Escenario 6 de quickstart.md (FR-015, FR-016).

Registrar la colocación de un producto en anaquel destacado / mailer por tienda y
semana; consultar su efecto en ventas frente a una semana de referencia, sin
atribución causal automática.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_registro_colocacion_y_efecto(client, escenario_promociones, auth_mkt, db_session):
    e = escenario_promociones

    # una ubicación de anaquel del catálogo sembrado del dataset
    codigo = await db_session.scalar(text("SELECT codigo FROM display_locations LIMIT 1"))
    if codigo is None:
        codigo = await db_session.scalar(
            text(
                "INSERT INTO display_locations (codigo, descripcion) "
                "VALUES ('ZZ', 'Anaquel test') RETURNING codigo"
            )
        )

    # ventas del producto A: 3 en la semana 20, 1 en la semana 19 (referencia)
    for semana, n in ((20, 3), (19, 1)):
        for _ in range(n):
            venta_id = await db_session.scalar(
                text(
                    "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
                    "VALUES (:t, :c, :f, :sem, 0, 'confirmada') RETURNING venta_id"
                ),
                {
                    "t": e["tienda_id"],
                    "c": e["cajero_id"],
                    "f": datetime(2025, 5, 15, tzinfo=UTC).replace(tzinfo=None),
                    "sem": semana,
                },
            )
            await db_session.execute(
                text(
                    "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
                    "VALUES (:v, :p, 1, 3.00)"
                ),
                {"v": venta_id, "p": e["product_a"]},
            )
    await db_session.flush()

    creada = await client.post(
        "/api/promociones/colocaciones",
        json={
            "product_id": e["product_a"],
            "tienda_id": e["tienda_id"],
            "display_location": codigo,
            "semana": 20,
            "anio": 2025,
        },
        headers=auth_mkt,
    )
    assert creada.status_code == 201, creada.text
    promocion_id = creada.json()["promocion_id"]

    listado = (
        await client.get(
            f"/api/promociones/colocaciones?tienda_id={e['tienda_id']}&semana=20&anio=2025",
            headers=auth_mkt,
        )
    ).json()
    assert any(c["promocion_id"] == promocion_id for c in listado)

    efecto = (
        await client.get(f"/api/promociones/colocaciones/{promocion_id}/efecto", headers=auth_mkt)
    ).json()
    assert efecto["ventas_semana_colocacion"] == 3
    assert efecto["ventas_semana_referencia"] == 1


async def test_colocacion_requiere_una_ubicacion(client, escenario_promociones, auth_mkt):
    e = escenario_promociones
    resp = await client.post(
        "/api/promociones/colocaciones",
        json={"product_id": e["product_a"], "tienda_id": e["tienda_id"], "semana": 1, "anio": 2025},
        headers=auth_mkt,
    )
    assert resp.status_code == 422, resp.text
