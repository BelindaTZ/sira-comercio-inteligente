"""Lógica pura de RRHH (feature 011) — sin acceso a datos (Principio V/XI).

- `parse_periodo`: interpreta el string `'AAAA-Sn'` de `clima_laboral.periodo` como
  un rango de fechas semestral (research.md Decisión 3).
- `tasa_rotacion`: fórmula de rotación por tienda/periodo a partir de conteos ya
  agregados; devuelve `None` cuando no hay plantilla base (FR-010, sin dato
  inventado).
- `marcar_sin_cobertura`: señala los puestos críticos sin ningún candidato de
  sucesión (FR-009).
"""

from __future__ import annotations

from datetime import date

_SEMESTRES = {1: ((1, 1), (6, 30)), 2: ((7, 1), (12, 31))}


class PeriodoInvalido(ValueError):
    """El string de periodo no tiene el formato `'AAAA-Sn'` (n = 1 ó 2)."""


def parse_periodo(periodo: str) -> tuple[date, date]:
    """`'2026-S2'` → `(date(2026, 7, 1), date(2026, 12, 31))` (ambas inclusive)."""
    texto = (periodo or "").strip().upper()
    anio_str, _, sem_str = texto.partition("-S")
    if not anio_str.isdigit() or sem_str not in {"1", "2"}:
        raise PeriodoInvalido(f"Periodo inválido: {periodo!r} (se espera 'AAAA-S1' o 'AAAA-S2')")
    anio = int(anio_str)
    (mi, di), (mf, df) = _SEMESTRES[int(sem_str)]
    return date(anio, mi, di), date(anio, mf, df)


def tasa_rotacion(*, bajas: int, plantilla_base: int) -> float | None:
    """`(bajas del periodo / plantilla al inicio del periodo) * 100`, redondeada a
    2 decimales. Sin plantilla base (0) no hay tasa: devuelve `None`, nunca 0
    inventado (FR-010)."""
    if not plantilla_base:
        return None
    return round(bajas / plantilla_base * 100, 2)


def marcar_sin_cobertura(puestos: list[dict]) -> list[dict]:
    """Anota cada puesto crítico con `sin_cobertura: bool` según tenga o no
    candidatos en su lista `candidatos` (FR-009)."""
    return [{**p, "sin_cobertura": not p.get("candidatos")} for p in puestos]
