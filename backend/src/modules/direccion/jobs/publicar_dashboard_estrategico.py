"""Job diario: publica el dashboard estratégico consolidado (feature 009, US1,
FR-001/FR-002/FR-008).

En producción lo dispara Airflow (010) tras el ELT del día; lee las agregaciones
pesadas de ClickHouse. Sin warehouse configurado (tests / desarrollo) toma los
valores ya calculados directamente de PostgreSQL en modo solo lectura
(`src/shared/dashboards.py`). En ambos casos inserta UNA fila en
`registro_publicacion_dashboard` (`tipo='estrategico'`) y sus `dashboard_kpi`
asociados — OE-4 siempre como no disponible (Principio VII), OE-8 con el valor
real de 011.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.direccion.repository import DireccionRepository
from src.shared.dashboards import kpis_estrategicos

logger = logging.getLogger("sira.jobs.publicar_dashboard_estrategico")

NOMBRE = "publicar_dashboard_estrategico_diario"


async def ejecutar(session: AsyncSession) -> dict:
    repo = DireccionRepository(session)
    try:
        kpis = await kpis_estrategicos(session)
    except Exception as exc:  # noqa: BLE001 - la corrida fallida también se registra (FR-008)
        pub = await repo.registrar_publicacion(exito=False, detalle_error=str(exc)[:2000])
        logger.exception("Publicación del dashboard estratégico falló")
        return {"job": NOMBRE, "publicacion_id": pub.publicacion_id, "exito": False}

    pub = await repo.registrar_publicacion(exito=True)
    for kpi in kpis:
        await repo.agregar_kpi(publicacion_id=pub.publicacion_id, **kpi)
    await repo.flush()
    return {
        "job": NOMBRE,
        "publicacion_id": pub.publicacion_id,
        "exito": True,
        "kpis": len(kpis),
    }


async def run(session_factory: async_sessionmaker) -> dict:
    async with session_factory() as session:
        resultado = await ejecutar(session)
        await session.commit()
    logger.info("Job %s: %s", NOMBRE, resultado)
    return resultado
