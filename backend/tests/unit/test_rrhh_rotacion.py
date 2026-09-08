"""T006/T023/T024 — lógica pura de clima/rotación (feature 011).

- `parse_periodo`: `'AAAA-Sn'` → rango de fechas semestral (research.md Decisión 3).
- `tasa_rotacion`: fórmula por tienda/periodo a partir de conteos agregados.
- Un periodo sin plantilla base devuelve `None`, nunca un indicador inventado
  (FR-010, Edge Case).
"""

from datetime import date

import pytest
from src.shared.rrhh import PeriodoInvalido, parse_periodo, tasa_rotacion


def test_parse_periodo_primer_semestre():
    assert parse_periodo("2026-S1") == (date(2026, 1, 1), date(2026, 6, 30))


def test_parse_periodo_segundo_semestre():
    assert parse_periodo("2026-S2") == (date(2026, 7, 1), date(2026, 12, 31))


def test_parse_periodo_tolera_espacios_y_minuscula():
    assert parse_periodo(" 2025-s2 ") == (date(2025, 7, 1), date(2025, 12, 31))


@pytest.mark.parametrize("malo", ["2026", "2026-S3", "2026S2", "S2-2026", "", "abcd-S1"])
def test_parse_periodo_invalido(malo):
    with pytest.raises(PeriodoInvalido):
        parse_periodo(malo)


def test_tasa_rotacion_basica():
    # 2 bajas sobre una plantilla base de 8 → 25.0 %
    assert tasa_rotacion(bajas=2, plantilla_base=8) == 25.0


def test_tasa_rotacion_redondea_a_dos_decimales():
    assert tasa_rotacion(bajas=1, plantilla_base=3) == 33.33


def test_tasa_rotacion_sin_bajas_es_cero():
    assert tasa_rotacion(bajas=0, plantilla_base=5) == 0.0


def test_tasa_rotacion_sin_plantilla_es_none_no_cero():
    assert tasa_rotacion(bajas=0, plantilla_base=0) is None
