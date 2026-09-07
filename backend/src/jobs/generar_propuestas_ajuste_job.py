"""Job semanal: genera propuestas de ajuste de precio para las categorías con
regla de ajuste activa (feature 003, FR-005, research.md §2/§6).

`ejecutar(session)` corre sobre una sesión dada (endpoint de desarrollo);
`run(session_factory)` abre la suya y hace commit (scheduler periódico).
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("sira.jobs.propuestas_ajuste")

NOMBRE = "propuestas_ajuste_semanal"


async def ejecutar(session: AsyncSession) -> dict:
    from src.modules.pricing.repository import PricingRepository
    from src.modules.pricing.service import PricingService

    svc = PricingService(PricingRepository(session))
    return await svc.generar_propuestas_ajuste()


async def run(session_factory: async_sessionmaker) -> dict:
    async with session_factory() as session:
        resultado = await ejecutar(session)
        await session.commit()
    logger.info("Job %s: %s", NOMBRE, resultado)
    return resultado
