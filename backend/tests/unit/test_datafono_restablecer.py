"""T010 — al restablecer un datáfono fuera de servicio, la reevaluación de
conformidad produce `activo` o `requiere_actualizacion` según `version_firmware`
(FR-003, Edge Case, Principio X). Reutiliza la regla de 006 sin duplicarla.
"""

from src.shared.caja import estado_datafono_restablecido


def test_firmware_conforme_queda_activo():
    assert estado_datafono_restablecido("3.2.0", "3.0.0") == "activo"
    assert estado_datafono_restablecido("3.0.0", "3.0.0") == "activo"


def test_firmware_no_conforme_queda_requiere_actualizacion():
    assert estado_datafono_restablecido("2.9.0", "3.0.0") == "requiere_actualizacion"
    assert estado_datafono_restablecido(None, "3.0.0") == "requiere_actualizacion"


def test_sin_estandar_vigente_queda_activo():
    assert estado_datafono_restablecido("1.0.0", None) == "activo"


def test_nunca_devuelve_fuera_servicio():
    for fw in ("2.0.0", "9.9.9", None, ""):
        assert estado_datafono_restablecido(fw, "3.0.0") in ("activo", "requiere_actualizacion")
