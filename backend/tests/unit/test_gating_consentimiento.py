"""T010 — gating de consentimiento (FR-001, Principio X).

Un cliente con `consentimiento_datos = false` (o inactivo) nunca aparece en el
resultado del repository que alimenta CLV / churn / campañas.
"""

import pytest
from sqlalchemy import text
from src.modules.clientes.repository import ClientesRepository

pytestmark = pytest.mark.asyncio


async def _crear_cliente(db_session, *, consent: bool, activo: bool = True) -> int:
    return await db_session.scalar(
        text(
            "INSERT INTO clientes (nombre, email, consentimiento_datos, activo) "
            "VALUES ('X', 'gate-' || gen_random_uuid()::text || '@e.com', :c, :a) "
            "RETURNING household_id"
        ),
        {"c": consent, "a": activo},
    )


async def test_solo_clientes_con_consentimiento_y_activos_son_elegibles(db_session):
    con = await _crear_cliente(db_session, consent=True)
    sin = await _crear_cliente(db_session, consent=False)
    inactivo = await _crear_cliente(db_session, consent=True, activo=False)
    await db_session.flush()

    repo = ClientesRepository(db_session)
    elegibles = set(await repo.household_ids_elegibles())

    assert con in elegibles
    assert sin not in elegibles
    assert inactivo not in elegibles


async def test_es_elegible_por_household_id(db_session):
    con = await _crear_cliente(db_session, consent=True)
    sin = await _crear_cliente(db_session, consent=False)
    await db_session.flush()

    repo = ClientesRepository(db_session)
    assert await repo.es_elegible(con) is True
    assert await repo.es_elegible(sin) is False
    assert await repo.es_elegible(99_999_999) is False


async def test_revocar_consentimiento_lo_saca_de_elegibles(db_session):
    hid = await _crear_cliente(db_session, consent=True)
    await db_session.flush()
    repo = ClientesRepository(db_session)
    assert hid in set(await repo.household_ids_elegibles())

    await db_session.execute(
        text("UPDATE clientes SET consentimiento_datos = false WHERE household_id = :h"),
        {"h": hid},
    )
    await db_session.flush()
    assert hid not in set(await repo.household_ids_elegibles())
