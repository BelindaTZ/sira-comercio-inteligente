"""Job semanal: calcula el WAPE del modelo vigente en producción contra la
demanda real de la semana ya cerrada y alerta si se degrada (feature 004, FR-011).
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("sira.jobs.monitorear_precision")

NOMBRE = "monitorear_precision_semanal"


async def ejecutar(session: AsyncSession) -> dict:
    from src.modules.forecasting.repository import ForecastingRepository
    from src.modules.forecasting.service import ForecastingService

    svc = ForecastingService(ForecastingRepository(session))
    return await svc.calcular_monitoreo_semanal()


async def run(session_factory: async_sessionmaker) -> dict:
    async with session_factory() as session:
        resultado = await ejecutar(session)
        await session.commit()
    logger.info("Job %s: %s", NOMBRE, resultado)
    return resultado
