"""T027 + T028 — transición de un incidente de seguridad de pago
(`abierto` → `en_investigacion` → `cerrado`) y su independencia de la máquina de
estados del incidente de fraude de 006 (FR-009, FR-010, Principio X).
"""

import pytest
from src.shared.caja import siguiente_estado_incidente
from src.shared.pagos import siguiente_estado_incidente_seguridad


def test_ciclo_completo():
    assert siguiente_estado_incidente_seguridad("abierto", "en_investigacion") == "en_investigacion"
    assert siguiente_estado_incidente_seguridad("en_investigacion", "cerrado") == "cerrado"


def test_transiciones_invalidas():
    with pytest.raises(ValueError):
        siguiente_estado_incidente_seguridad("abierto", "cerrado")  # salta un paso
    with pytest.raises(ValueError):
        siguiente_estado_incidente_seguridad("cerrado", "en_investigacion")
    with pytest.raises(ValueError):
        siguiente_estado_incidente_seguridad("en_investigacion", "abierto")


def test_independiente_de_la_maquina_de_fraude_de_006():
    # El incidente de seguridad (007) usa estados nuevos; el de fraude (006) usa
    # acciones. Ni el vocabulario ni los estados intermedios se solapan.
    assert siguiente_estado_incidente_seguridad("abierto", "en_investigacion") == "en_investigacion"
    assert siguiente_estado_incidente("abierto", "aplicar_protocolo") == "en_revision"
    # 'en_investigacion' no es un estado válido para el de fraude
    with pytest.raises(ValueError):
        siguiente_estado_incidente("en_investigacion", "cerrar")
    # 'aplicar_protocolo' no es una transición válida para el de seguridad
    with pytest.raises(ValueError):
        siguiente_estado_incidente_seguridad("abierto", "aplicar_protocolo")
