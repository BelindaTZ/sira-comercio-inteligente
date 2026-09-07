"""Job de promociones inteligentes (feature 005).

Ver `PromocionesService.calcular_afinidad`.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("sira.jobs.afinidad")

NOMBRE = "calcular_afinidad_mensual"


async def ejecutar(session: AsyncSession) -> dict:
    from src.modules.promociones.repository import PromocionesRepository
    from src.modules.promociones.service import PromocionesService

    svc = PromocionesService(PromocionesRepository(session))
    return await svc.calcular_afinidad()


async def run(session_factory: async_sessionmaker) -> dict:
    async with session_factory() as session:
        resultado = await ejecutar(session)
        await session.commit()
    logger.info("Job %s: %s", NOMBRE, resultado)
    return resultado
