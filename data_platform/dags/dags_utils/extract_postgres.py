"""Extract — lee la tabla origen de una entidad del modelo desde PostgreSQL
(feature 010, US2). Primer paso del ELT (Principio III: Extract → Load raw →
Load → Transform in-warehouse).

Una carga `completa` trae todo el histórico (FR-003). Una `incremental` filtra
por la columna de marca temporal de la tabla origen mayor a la fecha de fin de
la última corrida **exitosa** de esa entidad (research.md Decisión 3) — así una
corrida fallida a medias nunca avanza el punto de corte.

`_WATERMARK` mapea entidad → expresión SQL de la columna de modificación. `None`
= la tabla origen no tiene marca temporal (`cajas`): siempre se recarga completa
(tabla chica).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# entidad del modelo → SELECT que proyecta exactamente las columnas del schema de
# ClickHouse (data_platform/clickhouse/schema_warehouse.sql).
_SELECT: dict[str, str] = {
    "fact_venta": """
        SELECT vd.venta_detalle_id, v.venta_id, v.fecha_hora, v.semana,
               v.tienda_id, v.cajero_id, COALESCE(v.household_id, 0) AS household_id,
               vd.product_id, vd.cantidad, vd.sales_value, vd.retail_disc,
               vd.coupon_disc,
               CASE WHEN v.estado = 'anulada' THEN 1 ELSE 0 END AS anulada
        FROM venta_detalle vd
        JOIN ventas v ON v.venta_id = vd.venta_id
    """,
    "dim_cliente": """
        SELECT c.household_id, c.fecha_registro, c.activo,
               COALESCE(d.age, '') AS age, COALESCE(d.income, '') AS income,
               COALESCE(d.marital_status, '') AS marital_status
        FROM clientes c
        LEFT JOIN clientes_demograficos d ON d.household_id = c.household_id
    """,
    "dim_producto": """
        SELECT product_id, COALESCE(product_category,'') AS product_category,
               COALESCE(product_type,'') AS product_type, COALESCE(department,'') AS department,
               COALESCE(brand,'') AS brand, es_perecedero,
               COALESCE(clasificacion_abc,'') AS clasificacion_abc
        FROM productos
    """,
    "dim_tienda": """
        SELECT tienda_id, codigo, nombre, COALESCE(ciudad,'') AS ciudad, activa
        FROM tiendas
    """,
    "dim_caja": "SELECT caja_id, tienda_id, nombre, activa FROM cajas",
    "dim_empleado": """
        SELECT empleado_id, COALESCE(tienda_id, 0) AS tienda_id, nombre,
               fecha_contratacion, activo
        FROM empleados
    """,
}

# Expresión de la columna de watermark, con el alias correcto de su SELECT.
_WATERMARK: dict[str, str | None] = {
    "fact_venta": "v.fecha_hora",
    "dim_cliente": "c.updated_at",
    "dim_producto": "updated_at",
    "dim_tienda": "updated_at",
    "dim_caja": None,
    "dim_empleado": "updated_at",
}


@dataclass
class ExtractResult:
    rows: list[dict]
    tipo_carga: str  # 'completa' | 'incremental'


async def extraer(
    session, nombre_entidad: str, desde: datetime | None
) -> ExtractResult:
    """`session` es una AsyncSession de SQLAlchemy (misma infra que el backend).
    `desde` None → carga completa; un datetime → incremental sobre el watermark."""
    from sqlalchemy import text

    if nombre_entidad not in _SELECT:
        raise ValueError(
            f"Entidad '{nombre_entidad}' sin SELECT de extracción definido"
        )

    sql = _SELECT[nombre_entidad].strip()
    wm = _WATERMARK.get(nombre_entidad)
    params: dict = {}
    tipo = "completa"

    if desde is not None and wm is not None:
        # `>=` (no `>`): reprocesar la fila del borde no cuesta nada —
        # ReplacingMergeTree la deduplica (research.md Decisión 3) — y evita
        # perder una fila escrita en el mismo instante que cerró la corrida previa.
        sql = f"{sql} WHERE {wm} >= :desde"
        params["desde"] = desde
        tipo = "incremental"

    result = await session.execute(text(sql), params)
    return ExtractResult(rows=[dict(r._mapping) for r in result], tipo_carga=tipo)
