"""Refresca el snapshot `catalogo_kpi` (feature 013).

Los KPIs de la cabecera del Catálogo agregan sobre todo el histórico de ventas
(margen bruto ponderado, huella promocional). No se calculan por request —
mismo criterio que los KPIs de los dashboards de la feature 009.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("sira.jobs.catalogo_kpi")

NOMBRE = "refrescar_catalogo_kpi"


async def ejecutar(session: AsyncSession) -> dict:
    from src.modules.catalogo.repository import CatalogoRepository

    repo = CatalogoRepository(session)
    datos = await repo.calcular_resumen_kpi()
    await repo.guardar_resumen_kpi(datos)
    return {"total_activos": datos.get("total_activos"), "refrescado": True}


async def run(session_factory: async_sessionmaker) -> dict:
    async with session_factory() as session:
        resultado = await ejecutar(session)
        await session.commit()
    logger.info("Job %s: %s", NOMBRE, resultado)
    return resultado
