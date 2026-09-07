"""Orden determinístico de consumo de lotes FIFO/FEFO (research.md #4, FR-005).

Regla: `fecha_vencimiento ASC NULLS LAST, cantidad_recibida ASC, lote_id ASC`.
El desempate por `cantidad_recibida` y luego `lote_id` cubre el Edge Case del
spec (dos lotes con la misma fecha de vencimiento).

El repositorio replica este mismo orden en SQL con `FOR UPDATE` (el orden del
bloqueo debe vivir en la consulta); esta función es la definición canónica,
reutilizable y testeable de la regla.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, TypeVar


class LoteOrdenable(Protocol):
    fecha_vencimiento: date | None
    cantidad_recibida: int
    lote_id: int


T = TypeVar("T", bound=LoteOrdenable)

# Centinela para "sin fecha de vencimiento" → va al final (NULLS LAST).
_SIN_VENCIMIENTO = date.max


def clave_fifo_fefo(
    fecha_vencimiento: date | None, cantidad_recibida: int, lote_id: int
) -> tuple[date, int, int]:
    return (fecha_vencimiento or _SIN_VENCIMIENTO, cantidad_recibida, lote_id)


def ordenar_lotes_fifo_fefo(lotes: list[T]) -> list[T]:
    return sorted(
        lotes,
        key=lambda lote: clave_fifo_fefo(
            lote.fecha_vencimiento, lote.cantidad_recibida, lote.lote_id
        ),
    )
