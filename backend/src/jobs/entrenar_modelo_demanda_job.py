"""Job mensual: entrena una nueva versión del modelo de pronóstico de demanda y
la deja pendiente de aprobación (feature 004, FR-001, research.md Decisión 8).
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("sira.jobs.entrenar_modelo")

NOMBRE = "entrenar_modelo_demanda_mensual"


async def ejecutar(session: AsyncSession) -> dict:
    from src.modules.forecasting.repository import ForecastingRepository
    from src.modules.forecasting.service import ForecastingService

    svc = ForecastingService(ForecastingRepository(session))
    return await svc.entrenar_modelo()


async def run(session_factory: async_sessionmaker) -> dict:
    async with session_factory() as session:
        resultado = await ejecutar(session)
        await session.commit()
    logger.info("Job %s: %s", NOMBRE, resultado)
    return resultado
