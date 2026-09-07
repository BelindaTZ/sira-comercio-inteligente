"""T035 — integración US4: Escenario 6 de quickstart.md (FR-014, SC-005).

El reporte mensual consolida `eventos_quiebre_stock` por tienda y categoría; una
tienda/categoría sin eventos no aparece forzada a cero.
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_reporte_demanda_perdida_por_tienda_y_categoria(
    client, escenario_forecasting, auth_jefe_ops_fc, db_session
):
    e = escenario_forecasting

    # segunda categoría / segundo producto
    otro_pid = await db_session.scalar(text("SELECT COALESCE(MAX(product_id),0)+1 FROM productos"))
    await db_session.execute(
        text(
            "INSERT INTO productos (product_id, product_category, product_type, costo, "
            "precio_base) VALUES (:p, 'OTRA CAT', 'X', 1.0, 2.0)"
        ),
        {"p": otro_pid},
    )

    async def _quiebre(product_id, demanda):
        await db_session.execute(
            text(
                "INSERT INTO eventos_quiebre_stock "
                "(product_id, tienda_id, empleado_id, demanda_estimada_no_satisfecha, fecha_hora) "
                "VALUES (:p, :t, :emp, :d, :f)"
            ),
            {
                "p": product_id,
                "t": e["tienda_id"],
                "emp": e["cajero_id"],
                "d": demanda,
                "f": datetime.now(UTC).replace(tzinfo=None),
            },
        )

    await _quiebre(e["product_id"], 5)
    await _quiebre(e["product_id"], 3)
    await _quiebre(otro_pid, 10)
    await db_session.flush()

    hoy = date.today()
    reporte = (
        await client.get(
            "/api/forecasting/reportes/demanda-perdida",
            params={
                "fecha_desde": (hoy - timedelta(days=1)).isoformat(),
                "fecha_hasta": (hoy + timedelta(days=1)).isoformat(),
            },
            headers=auth_jefe_ops_fc,
        )
    ).json()

    por_cat = {f["product_category"]: f for f in reporte if f["tienda_id"] == e["tienda_id"]}
    assert por_cat["TEST CAT"]["cantidad_eventos"] == 2
    assert por_cat["TEST CAT"]["demanda_estimada_no_satisfecha"] == 8
    assert por_cat["OTRA CAT"]["cantidad_eventos"] == 1
    # una categoría sin eventos simplemente no aparece
    assert "CATEGORIA FANTASMA" not in por_cat


async def test_jefe_ti_no_ve_el_reporte_de_operaciones(client, escenario_forecasting, auth_jefe_ti):
    hoy = date.today()
    resp = await client.get(
        "/api/forecasting/reportes/demanda-perdida",
        params={"fecha_desde": hoy.isoformat(), "fecha_hasta": hoy.isoformat()},
        headers=auth_jefe_ti,
    )
    assert resp.status_code == 403, resp.text
