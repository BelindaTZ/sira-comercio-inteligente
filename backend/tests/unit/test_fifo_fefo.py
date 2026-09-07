"""T021 — orden determinístico de consumo FIFO/FEFO.

Regla: `fecha_vencimiento ASC NULLS LAST, cantidad_recibida ASC, lote_id ASC`
(research.md #4). Cubre el Edge Case del spec (misma fecha de vencimiento).
"""

from dataclasses import dataclass
from datetime import date

from src.shared.inventario_fifo import clave_fifo_fefo, ordenar_lotes_fifo_fefo


@dataclass
class L:
    lote_id: int
    cantidad_recibida: int
    fecha_vencimiento: date | None


def _ids(lotes):
    return [lote.lote_id for lote in lotes]


def test_vence_antes_sale_primero():
    lotes = [
        L(1, 10, date(2026, 12, 1)),
        L(2, 10, date(2026, 6, 1)),
        L(3, 10, date(2026, 9, 1)),
    ]
    assert _ids(ordenar_lotes_fifo_fefo(lotes)) == [2, 3, 1]


def test_sin_fecha_de_vencimiento_va_al_final():
    lotes = [L(1, 10, None), L(2, 10, date(2026, 6, 1))]
    assert _ids(ordenar_lotes_fifo_fefo(lotes)) == [2, 1]


def test_misma_fecha_desempata_por_cantidad_luego_lote_id():
    fv = date(2026, 6, 1)
    lotes = [L(10, 50, fv), L(11, 20, fv), L(12, 20, fv)]
    # cantidad ASC: 20 (lote 11), 20 (lote 12 — desempata lote_id), 50 (lote 10)
    assert _ids(ordenar_lotes_fifo_fefo(lotes)) == [11, 12, 10]


def test_orden_es_estable_y_no_muta_la_entrada():
    lotes = [L(3, 5, None), L(1, 5, None), L(2, 5, None)]
    ordenados = ordenar_lotes_fifo_fefo(lotes)
    assert _ids(ordenados) == [1, 2, 3]
    assert _ids(lotes) == [3, 1, 2]


def test_clave_pone_los_nulos_al_final():
    assert clave_fifo_fefo(None, 1, 1)[0] == date.max
