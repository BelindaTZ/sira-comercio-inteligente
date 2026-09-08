"""T020 — identificación de un datáfono no conforme comparando `version_firmware`
contra la versión mínima vigente (FR-007, research.md Decisión 4, Principio X).
"""

from src.shared.caja import datafono_no_conforme


def test_firmware_por_debajo_del_minimo_es_no_conforme():
    assert datafono_no_conforme("2.9.0", "3.2.0") is True


def test_firmware_igual_o_superior_es_conforme():
    assert datafono_no_conforme("3.2.0", "3.2.0") is False
    assert datafono_no_conforme("3.10.0", "3.2.0") is False  # 10 > 2, no comparación lexicográfica


def test_sin_firmware_declarado_es_no_conforme():
    assert datafono_no_conforme(None, "3.2.0") is True
    assert datafono_no_conforme("", "3.2.0") is True


def test_sin_estandar_vigente_nada_es_no_conforme_todavia():
    assert datafono_no_conforme("1.0.0", None) is False


def test_tolera_versiones_de_distinto_largo():
    assert datafono_no_conforme("3.2", "3.2.1") is True
    assert datafono_no_conforme("3.2.0", "3.2") is False
