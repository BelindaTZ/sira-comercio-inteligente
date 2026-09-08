"""T037 — transición de estado de un incidente de fraude: abierto → en_revision →
cerrado, y que la regla no mira el estado del empleado (FR-015/FR-016, Principio X).
"""

import pytest
from src.shared.caja import siguiente_estado_incidente


def test_ciclo_completo():
    assert siguiente_estado_incidente("abierto", "aplicar_protocolo") == "en_revision"
    assert siguiente_estado_incidente("en_revision", "cerrar") == "cerrado"


def test_no_se_puede_cerrar_un_incidente_abierto():
    with pytest.raises(ValueError):
        siguiente_estado_incidente("abierto", "cerrar")


def test_no_se_puede_reaplicar_protocolo_en_revision():
    with pytest.raises(ValueError):
        siguiente_estado_incidente("en_revision", "aplicar_protocolo")


def test_no_se_puede_transicionar_un_incidente_cerrado():
    with pytest.raises(ValueError):
        siguiente_estado_incidente("cerrado", "cerrar")
    with pytest.raises(ValueError):
        siguiente_estado_incidente("cerrado", "aplicar_protocolo")


def test_la_transicion_no_depende_del_empleado():
    # La función sólo recibe estado + acción: no hay forma de que la baja de un
    # empleado bloquee la transición (FR-016).
    assert siguiente_estado_incidente("en_revision", "cerrar") == "cerrado"
