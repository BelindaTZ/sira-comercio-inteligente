"""Transform in-warehouse — último paso del ELT (feature 010, Principio III:
la transformación ocurre DENTRO del warehouse, no antes de cargarlo).

Para la primera versión la transformación es mínima: forzar el merge de
`ReplacingMergeTree` para que las lecturas de 009 no vean duplicados transitorios
de una recarga incremental (`OPTIMIZE TABLE ... FINAL`). No recalcula ningún KPI
de negocio (eso es de 009).

`cliente_ch` es cualquier objeto con `command(sql: str)`.
"""

from __future__ import annotations

_TABLA: dict[str, str] = {
    "fact_venta": "fact_venta",
    "dim_cliente": "dim_cliente",
    "dim_producto": "dim_producto",
    "dim_tienda": "dim_tienda",
    "dim_caja": "dim_caja",
    "dim_empleado": "dim_empleado",
}


def transformar(cliente_ch, *, nombre_entidad: str) -> None:
    tabla = _TABLA.get(nombre_entidad)
    if tabla is None:
        return
    cliente_ch.command(f"OPTIMIZE TABLE sira_warehouse.{tabla} FINAL")
