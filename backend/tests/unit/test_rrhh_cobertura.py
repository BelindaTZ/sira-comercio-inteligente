"""T030 — señalización de puestos críticos sin candidato de sucesión (FR-009).

`marcar_sin_cobertura` es lógica pura; el servicio la aplica sobre la consulta
`roles_puesto.es_critico = true LEFT JOIN plan_sucesion`.
"""

from src.shared.rrhh import marcar_sin_cobertura


def test_puesto_sin_candidatos_se_marca_sin_cobertura():
    salida = marcar_sin_cobertura([{"puesto_id": 1, "nombre": "Encargado", "candidatos": []}])
    assert salida[0]["sin_cobertura"] is True


def test_puesto_con_candidatos_no_se_marca():
    salida = marcar_sin_cobertura(
        [{"puesto_id": 2, "nombre": "Analista", "candidatos": [{"empleado_candidato_id": 9}]}]
    )
    assert salida[0]["sin_cobertura"] is False


def test_campo_candidatos_ausente_cuenta_como_sin_cobertura():
    salida = marcar_sin_cobertura([{"puesto_id": 3, "nombre": "Cajero Sr"}])
    assert salida[0]["sin_cobertura"] is True
