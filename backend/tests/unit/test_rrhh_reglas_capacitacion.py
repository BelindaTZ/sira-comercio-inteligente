"""T015/T016 — reglas de capacitación (feature 011), sobre la BD real.

- T015: el fan-out al programar una capacitación alcanza sólo a empleados con
  cuenta de usuario activa en los roles objetivo; un empleado sin cuenta NO queda
  incluido (FR-003/FR-004, research.md Decisión 2).
- T016: la consulta de cumplimiento restringe al Encargado de Tienda a su propia
  tienda (FR-005).
"""

import pytest
from src.modules.rrhh.repository import RRHHRepository
from src.modules.rrhh.service import RRHHService
from src.shared.exceptions import ForbiddenError

pytestmark = pytest.mark.asyncio


def _svc(db_session) -> RRHHService:
    return RRHHService(RRHHRepository(db_session))


async def test_fanout_solo_empleados_con_cuenta_activa(db_session, escenario_rrhh):
    e = escenario_rrhh
    svc = _svc(db_session)

    resultado = await svc.programar_capacitacion(
        nombre="Uso de dashboards", descripcion=None, role_ids=[e["rol_cajero_id"]]
    )
    # A1 y A2 (con cuenta) + B1 (con cuenta) = 3; el cajero A sin cuenta queda fuera.
    assert resultado["empleados_asignados"] == 3

    filas = await RRHHRepository(db_session).cumplimiento_por_tienda(e["tienda_a"])
    asignados_a = {f["empleado_id"] for f in filas}
    assert e["cajero_a1"] in asignados_a
    assert e["cajero_a2"] in asignados_a
    assert e["cajero_a_sin_cuenta"] not in asignados_a


async def test_encargado_restringido_a_su_tienda(db_session, escenario_rrhh):
    e = escenario_rrhh
    svc = _svc(db_session)

    # su propia tienda: permitido
    await svc.cumplimiento_tienda(
        e["tienda_a"], tienda_actor=e["tienda_a"], restringir_a_tienda=True
    )
    # otra tienda: prohibido
    with pytest.raises(ForbiddenError):
        await svc.cumplimiento_tienda(
            e["tienda_b"], tienda_actor=e["tienda_a"], restringir_a_tienda=True
        )
