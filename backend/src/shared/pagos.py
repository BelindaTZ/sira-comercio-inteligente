"""Lógica pura de pagos y seguridad (feature 007, Principio X).

Sin I/O — cada función es la definición canónica y testeable de una regla:

  - `medio_pago_disponible` — se ofrece en caja solo si aprobado y sin baja (FR-007)
  - `siguiente_estado_incidente_seguridad` — abierto → en_investigacion → cerrado (FR-009)
  - `duracion_cobro_segundos` — duración de una venta, excluye anuladas y sin inicio (FR-015/18)
  - `promedio_duracion_cobro` — promedio + conteo sobre un conjunto de ventas
"""

from __future__ import annotations

from datetime import datetime

ESTADOS_INCIDENTE_SEGURIDAD = ("abierto", "en_investigacion", "cerrado")

_TRANSICIONES: dict[tuple[str, str], bool] = {
    ("abierto", "en_investigacion"): True,
    ("en_investigacion", "cerrado"): True,
}


def _campo(fila, nombre):
    return fila[nombre] if isinstance(fila, dict) else getattr(fila, nombre)


# ============================================================ medios de pago (US2)
def medio_pago_disponible(aprobado, fecha_baja) -> bool:
    """FR-007 — un medio de pago se ofrece en el punto de venta únicamente si está
    aprobado y no ha sido dado de baja."""
    return bool(aprobado) and fecha_baja is None


# ============================================================ incidente de seguridad (US3)
def siguiente_estado_incidente_seguridad(estado_actual: str, estado_nuevo: str) -> str:
    """FR-009 — valida la transición de un incidente de seguridad de pago
    (`abierto` → `en_investigacion` → `cerrado`). Lanza `ValueError` si no es
    válida (el service lo traduce a 409). Es una máquina de estados propia,
    independiente de la de `incidentes_fraude` de 006 (FR-010) — no comparte
    vocabulario de acciones ni de estados intermedios.
    """
    if _TRANSICIONES.get((estado_actual, estado_nuevo)):
        return estado_nuevo
    raise ValueError(
        f"Transición inválida de incidente de seguridad: '{estado_actual}' → '{estado_nuevo}'"
    )


# ============================================================ tiempo de cobro (US5)
def duracion_cobro_segundos(
    fecha_inicio_cobro: datetime | None, fecha_hora: datetime | None, estado: str
) -> float | None:
    """FR-015/FR-018 — duración del cobro de una venta, en segundos
    (`fecha_hora - fecha_inicio_cobro`). Devuelve `None` (queda fuera de todo
    promedio) cuando la venta está anulada, no tiene `fecha_inicio_cobro`
    (venta previa a 007 o sembrada del dataset), o el resultado sería negativo.
    """
    if estado == "anulada" or fecha_inicio_cobro is None or fecha_hora is None:
        return None
    segundos = (fecha_hora - fecha_inicio_cobro).total_seconds()
    return segundos if segundos >= 0 else None


def promedio_duracion_cobro(ventas) -> tuple[float | None, int]:
    """Promedio de `duracion_cobro_segundos` sobre las ventas consideradas
    (las que devuelven un valor no-None) y su conteo. `(None, 0)` si ninguna
    venta califica."""
    duraciones = [
        d
        for v in ventas
        if (
            d := duracion_cobro_segundos(
                _campo(v, "fecha_inicio_cobro"), _campo(v, "fecha_hora"), _campo(v, "estado")
            )
        )
        is not None
    ]
    if not duraciones:
        return None, 0
    return round(sum(duraciones) / len(duraciones), 2), len(duraciones)
