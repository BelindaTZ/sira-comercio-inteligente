"""T011 + T012 — integración US1: Escenarios 1 y 2 de quickstart.md.

Calcular afinidad → recomendar cross-sell con el antecedente en el carrito →
agregar el consecuente → la recomendación desaparece (FR-003/FR-004). Desactivar
una regla la saca de la evaluación (FR-002).
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_ciclo_afinidad_y_recomendacion(client, escenario_promociones, auth_mkt, auth_cajero):
    e = escenario_promociones

    calc = await client.post("/api/promociones/reglas-afinidad/calcular", headers=auth_mkt)
    assert calc.status_code == 201, calc.text
    assert calc.json()["reglas_generadas"] >= 1

    reglas = (
        await client.get("/api/promociones/reglas-afinidad?estado=vigente", headers=auth_mkt)
    ).json()
    par = {(r["product_id_antecedente"], r["product_id_consecuente"]) for r in reglas}
    assert (e["product_a"], e["product_b"]) in par or (e["product_b"], e["product_a"]) in par

    # carrito con A, sin B → recomienda B
    rec = (
        await client.get(
            f"/api/promociones/recomendacion-cross-sell?product_ids={e['product_a']}",
            headers=auth_cajero,
        )
    ).json()
    assert rec["recomendacion_disponible"] is True
    assert rec["product_id_recomendado"] == e["product_b"]

    # carrito con A y B → sin recomendación redundante (FR-004)
    rec2 = (
        await client.get(
            f"/api/promociones/recomendacion-cross-sell?product_ids={e['product_a']},{e['product_b']}",
            headers=auth_cajero,
        )
    ).json()
    assert rec2["recomendacion_disponible"] is False


async def test_desactivar_regla_la_saca_de_la_recomendacion(
    client, escenario_promociones, auth_mkt, auth_cajero
):
    e = escenario_promociones
    await client.post("/api/promociones/reglas-afinidad/calcular", headers=auth_mkt)
    reglas = (
        await client.get("/api/promociones/reglas-afinidad?estado=vigente", headers=auth_mkt)
    ).json()
    regla = next(
        r
        for r in reglas
        if r["product_id_antecedente"] == e["product_a"]
        and r["product_id_consecuente"] == e["product_b"]
    )

    off = await client.post(
        f"/api/promociones/reglas-afinidad/{regla['regla_id']}/desactivar",
        json={"motivo": "no accionable"},
        headers=auth_mkt,
    )
    assert off.status_code == 200 and off.json()["estado"] == "desactivada"

    # 409 al desactivar de nuevo
    otra = await client.post(
        f"/api/promociones/reglas-afinidad/{regla['regla_id']}/desactivar", headers=auth_mkt
    )
    assert otra.status_code == 409, otra.text

    rec = (
        await client.get(
            f"/api/promociones/recomendacion-cross-sell?product_ids={e['product_a']}",
            headers=auth_cajero,
        )
    ).json()
    assert rec["recomendacion_disponible"] is False


async def test_recomendacion_vacia_sin_reglas(client, escenario_promociones, auth_cajero):
    e = escenario_promociones
    rec = (
        await client.get(
            f"/api/promociones/recomendacion-cross-sell?product_ids={e['product_a']}",
            headers=auth_cajero,
        )
    ).json()
    assert rec["recomendacion_disponible"] is False
