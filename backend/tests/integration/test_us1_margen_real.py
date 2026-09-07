"""T011 — integración US1 (FR-002, FR-003).

Margen objetivo definido + margen real de una venta confirmada calculado con el
precio POST-descuento (nunca el de catálogo) y consultable por categoría.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_margen_real_usa_precio_descontado_y_es_consultable_por_categoria(
    client, escenario_pricing, auth_cajero, auth_pricing_jc, db_session
):
    e = escenario_pricing  # producto costo 1.00, precio 2.50, categoría 'TEST CAT'

    await client.patch(
        "/api/pricing/margenes/TEST CAT",
        json={"margen_objetivo_pct": "40"},
        headers=auth_pricing_jc,
    )

    venta = (
        await client.post(
            "/api/ventas",
            json={"tienda_id": e["tienda_id"], "cajero_id": e["cajero_id"]},
            headers=auth_cajero,
        )
    ).json()
    venta = (
        await client.post(
            f"/api/ventas/{venta['venta_id']}/lineas",
            json={"product_id": e["product_id"], "cantidad": 4},
            headers=auth_cajero,
        )
    ).json()
    linea_id = venta["lineas"][0]["venta_detalle_id"]

    # descuento manual: 2.00 sobre 4 uds (0.50/ud) → precio aplicado 2.00/ud
    await client.post(
        f"/api/ventas/{venta['venta_id']}/lineas/{linea_id}/descuento",
        json={
            "tipo": "monto",
            "valor": "2.00",
            "motivo": "cierre de lote",
            "empleado_aplica_id": e["cajero_id"],
            "empleado_autoriza_id": e["encargado_id"],
        },
        headers=auth_cajero,
    )

    confirm = await client.post(
        f"/api/ventas/{venta['venta_id']}/confirmar",
        json={"medio_pago_id": e["medio_efectivo"]},
        headers=auth_cajero,
    )
    assert confirm.status_code == 200, confirm.text

    # margen_real persistido con el precio ya descontado: (2.00 - 1.00)/2.00 = 50%
    margen_real = await db_session.scalar(
        text("SELECT margen_real FROM venta_detalle WHERE venta_detalle_id = :l"),
        {"l": linea_id},
    )
    assert float(margen_real) == 50.0

    hoy = date.today()
    reporte = (
        await client.get(
            "/api/pricing/reportes/margen",
            params={
                "fecha_desde": (hoy - timedelta(days=1)).isoformat(),
                "fecha_hasta": (hoy + timedelta(days=1)).isoformat(),
            },
            headers=auth_pricing_jc,
        )
    ).json()
    fila = next(f for f in reporte["filas"] if f["product_category"] == "TEST CAT")
    assert fila["margen_objetivo_pct"] == "40.00"
    assert float(fila["margen_real_pct"]) == 50.0  # ingreso 8.00, costo 4.00
