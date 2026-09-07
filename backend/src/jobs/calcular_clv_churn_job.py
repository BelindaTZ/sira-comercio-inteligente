"""Job semanal: recalcula CLV (US2) y churn/severidad (US3) de cada cliente
elegible (FR-005, FR-009, FR-010).

`ejecutar(session)` corre sobre una sesión dada (la usa el endpoint de desarrollo
con la sesión del request); `run(session_factory)` abre su propia sesión y hace
commit (la usa el scheduler periódico).
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("sira.jobs.clv_churn")

NOMBRE = "clv_churn_semanal"


async def ejecutar(session: AsyncSession) -> dict:
    from src.modules.clientes.repository import ClientesRepository
    from src.modules.clientes.service import ClientesService

    svc = ClientesService(ClientesRepository(session))
    return await svc.recalcular_clv_churn()


async def run(session_factory: async_sessionmaker) -> dict:
    async with session_factory() as session:
        resultado = await ejecutar(session)
        await session.commit()
    logger.info("Job %s: %s", NOMBRE, resultado)
    return resultado
