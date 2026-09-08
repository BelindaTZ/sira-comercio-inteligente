"""Lógica pura de caja, mermas y fraude (feature 006, Principio X).

Sin I/O — cada función es la definición canónica y testeable de una regla que el
service y el repository luego orquestan contra la BD:

  - `total_esperado_ventana` — ventas del cajero en la ventana horaria (FR-003, research §1/2)
  - `marcado_para_revision` — un cuadre con diferencia <> 0 se marca solo (FR-004)
  - `datafono_no_conforme` — firmware bajo la versión mínima vigente (FR-007, research §4)
  - `agrupar_diferencias_por_turno` — reporte por cajero+turno, no por tienda (FR-009)
  - `ajuste_inventario_anomalo` — ajuste de 001 con faltante sobre el umbral (FR-010)
  - `porcentaje_merma` — merma acumulada como % del valor de venta (FR-018, research §9)
  - `siguiente_estado_incidente` — transición abierto → en_revision → cerrado (FR-015)
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")


def _d(valor) -> Decimal:
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def _campo(fila, nombre):
    return fila[nombre] if isinstance(fila, dict) else getattr(fila, nombre)


# ============================================================ cuadre de caja (US1)
def total_esperado_ventana(ventas, *, desde: datetime, hasta: datetime) -> Decimal:
    """Suma de `total` de las ventas del cajero con `desde < fecha_hora <= hasta`
    (research.md Decisión 2 — la ventana no solapa con el cuadre anterior ni deja
    huecos). Una ventana sin ninguna venta devuelve `Decimal('0.00')`, nunca None:
    un cuadre con cero ventas esperadas es válido (FR-003, Edge Case).

    `ventas` es un iterable de filas con `fecha_hora` y `total` (dict o atributo).
    El filtrado por cajero y por estado != 'anulada' lo hace la consulta SQL; esta
    función asume que las filas ya vienen acotadas a un cajero.
    """
    total = Decimal("0")
    for v in ventas:
        fecha_hora = _campo(v, "fecha_hora")
        if desde < fecha_hora <= hasta:
            total += _d(_campo(v, "total"))
    return total.quantize(_CENT, rounding=ROUND_HALF_UP)


def marcado_para_revision(diferencia) -> bool:
    """FR-004 — cualquier diferencia distinta de cero marca el cuadre para revisión
    en el mismo momento en que se registra. `diferencia = 0` no genera marca."""
    return _d(diferencia) != 0


# ============================================================ datáfonos (US2)
def _partes_version(version: str) -> tuple[int, ...]:
    partes: list[int] = []
    for segmento in str(version).strip().split("."):
        digitos = "".join(ch for ch in segmento if ch.isdigit())
        partes.append(int(digitos) if digitos else 0)
    return tuple(partes) or (0,)


def datafono_no_conforme(version_firmware, version_minima) -> bool:
    """FR-007 / research.md Decisión 4 — un datáfono es no conforme cuando su
    `version_firmware` es menor que la versión mínima vigente en
    `configuracion_seguridad_pagos`. Sin firmware declarado se considera no
    conforme; sin estándar vigente nada es no conforme todavía.
    """
    if version_minima is None:
        return False
    if not version_firmware:
        return True
    actual = _partes_version(version_firmware)
    minima = _partes_version(version_minima)
    ancho = max(len(actual), len(minima))
    actual += (0,) * (ancho - len(actual))
    minima += (0,) * (ancho - len(minima))
    return actual < minima


def estado_datafono_restablecido(version_firmware, version_minima) -> str:
    """Feature 007 (FR-003) — al restablecer un datáfono `fuera_servicio` no se pasa
    directo a `activo`: se reevalúa su conformidad reutilizando `datafono_no_conforme`
    (la misma regla de 006, sin duplicarla). Devuelve `'requiere_actualizacion'` si
    su firmware no cumple el estándar vigente, `'activo'` si cumple.
    """
    return (
        "requiere_actualizacion"
        if datafono_no_conforme(version_firmware, version_minima)
        else "activo"
    )


# ============================================================ reporte mensual (US3)
def agrupar_diferencias_por_turno(cierres) -> list[dict]:
    """FR-009 / research.md Decisión 3 — agrupa los cuadres del mes por
    `cajero_id` + `apertura_id` (el turno), sumando la diferencia y contando
    cuántos cuadres del turno tuvieron diferencia. No colapsa al total de la
    tienda: cada (cajero, turno) es una fila propia.
    """
    grupos: dict[tuple[int, int], dict] = {}
    for cierre in cierres:
        cajero_id = _campo(cierre, "cajero_id")
        apertura_id = _campo(cierre, "apertura_id")
        clave = (cajero_id, apertura_id)
        grupo = grupos.setdefault(
            clave,
            {
                "cajero_id": cajero_id,
                "apertura_id": apertura_id,
                "fecha_turno": _campo(cierre, "fecha_turno"),
                "suma_diferencias": Decimal("0"),
                "cantidad_cuadres_con_diferencia": 0,
            },
        )
        diferencia = _d(_campo(cierre, "diferencia"))
        grupo["suma_diferencias"] += diferencia
        if diferencia != 0:
            grupo["cantidad_cuadres_con_diferencia"] += 1
    for grupo in grupos.values():
        grupo["suma_diferencias"] = grupo["suma_diferencias"].quantize(_CENT)
    return sorted(grupos.values(), key=lambda g: (g["cajero_id"], g["apertura_id"]))


def ajuste_inventario_anomalo(diferencia, umbral_unidades) -> bool:
    """FR-010 — un ajuste de inventario de 001 se señala en el reporte cuando su
    `diferencia` es negativa (faltante) y su magnitud alcanza o supera el umbral
    configurable (en unidades)."""
    valor = _d(diferencia)
    return valor < 0 and abs(valor) >= abs(_d(umbral_unidades))


# ============================================================ merma semanal (US5)
def porcentaje_merma(valor_merma, valor_ventas) -> Decimal | None:
    """FR-018 / research.md Decisión 9 — merma acumulada de la categoría/tienda en
    la semana como porcentaje del valor de venta de esa misma categoría/tienda en
    la misma semana. `None` si no hubo ventas (no hay base sobre la cual medir)."""
    ventas = _d(valor_ventas)
    if ventas <= 0:
        return None
    return (_d(valor_merma) / ventas * 100).quantize(_CENT, rounding=ROUND_HALF_UP)


def supera_umbral(porcentaje_merma_acumulado, porcentaje_umbral) -> bool:
    """FR-019 — informativo, nunca bloqueante. `None` (sin ventas) no supera nada."""
    if porcentaje_merma_acumulado is None or porcentaje_umbral is None:
        return False
    return _d(porcentaje_merma_acumulado) > _d(porcentaje_umbral)


# ============================================================ incidente de fraude (US4)
ESTADOS_INCIDENTE = ("abierto", "en_revision", "cerrado")

_TRANSICIONES: dict[tuple[str, str], str] = {
    ("abierto", "aplicar_protocolo"): "en_revision",
    ("en_revision", "cerrar"): "cerrado",
}


def siguiente_estado_incidente(estado_actual: str, accion: str) -> str:
    """FR-015 — devuelve el estado resultante de aplicar `accion` sobre un
    incidente en `estado_actual`. Lanza `ValueError` si la transición no es
    válida (el service lo traduce a 409). La regla no mira el estado del empleado
    involucrado: un incidente sobre alguien con `fecha_baja` transiciona igual
    (FR-016).
    """
    try:
        return _TRANSICIONES[(estado_actual, accion)]
    except KeyError as exc:
        raise ValueError(
            f"No se puede '{accion}' un incidente en estado '{estado_actual}'"
        ) from exc
