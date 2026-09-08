"""Load — inserta el lote extraído en ClickHouse (feature 010, US2/US3).

Idempotencia (FR-004): las tablas del warehouse son `ReplacingMergeTree` con la
clave natural como `ORDER BY` — reprocesar la misma ventana no duplica filas.
Este módulo sólo hace `INSERT`; la deduplicación la resuelve el motor (y el
`OPTIMIZE ... FINAL` de `transform_in_warehouse`).

Calidad (FR-007, research.md Decisión 4): dos reglas mínimas, verificadas en
Python sin motor de reglas configurable —
  1. referencia rota: una FK lógica a una dimensión cuyo valor no existe.
  2. campo obligatorio vacío: una columna requerida del destino en NULL/''.
La fila que rompe una regla NO se inserta y se reporta aparte; el resto del lote
continúa (nunca se detiene la corrida por un registro).

`cliente_ch` es cualquier objeto con `insert(tabla: str, filas: list[dict])`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

# entidad → (tabla destino, clave natural, columnas obligatorias, {columna_fk: dimension})
_DESTINO: dict[str, str] = {
    "fact_venta": "fact_venta",
    "dim_cliente": "dim_cliente",
    "dim_producto": "dim_producto",
    "dim_tienda": "dim_tienda",
    "dim_caja": "dim_caja",
    "dim_empleado": "dim_empleado",
}

_OBLIGATORIAS: dict[str, tuple[str, ...]] = {
    "fact_venta": (
        "venta_detalle_id",
        "venta_id",
        "fecha_hora",
        "product_id",
        "cantidad",
        "sales_value",
    ),
    "dim_cliente": ("household_id",),
    "dim_producto": ("product_id",),
    "dim_tienda": ("tienda_id", "codigo"),
    "dim_caja": ("caja_id", "tienda_id"),
    "dim_empleado": ("empleado_id",),
}

# columna del lote → nombre de dimensión de referencia (para la regla 1)
_REFERENCIAS: dict[str, dict[str, str]] = {
    "fact_venta": {"product_id": "dim_producto", "tienda_id": "dim_tienda"},
}


@dataclass
class LoadResult:
    filas_cargadas: int = 0
    filas_error: int = 0
    problemas: list[tuple[str, str | None]] = field(
        default_factory=list
    )  # (descripcion, identificador)


def _vacio(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def _identificador(nombre_entidad: str, fila: dict) -> str | None:
    pk = _OBLIGATORIAS[nombre_entidad][0]
    return f"{pk}={fila.get(pk)}" if fila.get(pk) is not None else None


def cargar(
    cliente_ch,
    *,
    nombre_entidad: str,
    filas: list[dict],
    claves_validas: dict[str, set] | None = None,
    on_issue: Callable[[str, str | None], None] | None = None,
) -> LoadResult:
    """`claves_validas` mapea nombre-de-dimensión → set de PKs válidas, para la
    regla de referencia rota (la pasa el DAG con las dims ya cargadas). Si una
    referencia no está en el dict, esa regla no se evalúa para esa columna."""
    if nombre_entidad not in _DESTINO:
        raise ValueError(f"Entidad '{nombre_entidad}' sin tabla destino definida")
    claves_validas = claves_validas or {}
    res = LoadResult()
    buenas: list[dict] = []

    for fila in filas:
        problema: str | None = None

        for col in _OBLIGATORIAS[nombre_entidad]:
            if _vacio(fila.get(col)):
                problema = f"campo obligatorio vacío: '{col}' en {nombre_entidad}"
                break

        if problema is None:
            for col, dim in _REFERENCIAS.get(nombre_entidad, {}).items():
                validas = claves_validas.get(dim)
                if validas is not None and fila.get(col) not in validas:
                    problema = (
                        f"referencia rota: {col} {fila.get(col)} no existe en {dim}"
                    )
                    break

        if problema is None:
            buenas.append(fila)
        else:
            res.filas_error += 1
            ident = _identificador(nombre_entidad, fila)
            res.problemas.append((problema, ident))
            if on_issue is not None:
                on_issue(problema, ident)

    if buenas:
        cliente_ch.insert(_DESTINO[nombre_entidad], buenas)
    res.filas_cargadas = len(buenas)
    return res
