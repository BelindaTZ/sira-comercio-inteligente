"""Job de promociones inteligentes (feature 005).

Ver `PromocionesService.generar_candidatos_liquidacion`.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("sira.jobs.candidatos")

NOMBRE = "candidatos_liquidacion_semanal"


async def ejecutar(session: AsyncSession) -> dict:
    from src.modules.promociones.repository import PromocionesRepository
    from src.modules.promociones.service import PromocionesService

    svc = PromocionesService(PromocionesRepository(session))
    return await svc.generar_candidatos_liquidacion()


async def run(session_factory: async_sessionmaker) -> dict:
    async with session_factory() as session:
        resultado = await ejecutar(session)
        await session.commit()
    logger.info("Job %s: %s", NOMBRE, resultado)
    return resultado
