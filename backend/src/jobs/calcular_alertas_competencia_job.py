"""Job semanal: refresca Open Prices (best-effort) para los productos en vivo con
código de barras real y recalcula las alertas de desviación de precio de
competencia (feature 003, FR-015/FR-016, research.md §5/§6).
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("sira.jobs.alertas_competencia")

NOMBRE = "alertas_competencia_semanal"


async def ejecutar(session: AsyncSession) -> dict:
    from src.modules.pricing.repository import PricingRepository
    from src.modules.pricing.service import PricingService

    svc = PricingService(PricingRepository(session))
    return await svc.refrescar_y_calcular_alertas_competencia()


async def run(session_factory: async_sessionmaker) -> dict:
    async with session_factory() as session:
        resultado = await ejecutar(session)
        await session.commit()
    logger.info("Job %s: %s", NOMBRE, resultado)
    return resultado
