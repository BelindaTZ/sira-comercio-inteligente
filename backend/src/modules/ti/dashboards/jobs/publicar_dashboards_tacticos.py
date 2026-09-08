"""Job diario: publica los dashboards tácticos por departamento (feature 009,
US2, FR-004/FR-008).

Una corrida por cada uno de los 6 módulos con Jefe propio (research.md Decisión
4), cada una con su propia fila en `registro_publicacion_dashboard`
(`tipo='tactico'`, `modulo_id`). En producción lee agregaciones de ClickHouse
(010); sin warehouse configurado toma los valores ya calculados de PostgreSQL
(`src/shared/dashboards.py`).
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.ti.dashboards.repository import TiDashboardsRepository
from src.shared.dashboards import MODULOS_TACTICOS, kpis_tacticos

logger = logging.getLogger("sira.jobs.publicar_dashboards_tacticos")

NOMBRE = "publicar_dashboards_tacticos_diario"


async def _publicar_uno(
    session: AsyncSession, repo: TiDashboardsRepository, modulo: str
) -> int | None:
    """Devuelve el `publicacion_id` de la corrida exitosa, o `None` si falló."""
    modulo_id = await session.scalar(
        text("SELECT modulo_id FROM modulos WHERE nombre = :n"), {"n": modulo}
    )
    if modulo_id is None:
        return None
    try:
        kpis = await kpis_tacticos(session, modulo)
    except Exception as exc:  # noqa: BLE001 - la corrida fallida también se registra (FR-008)
        await repo.registrar_publicacion(
            tipo_dashboard="tactico",
            modulo_id=modulo_id,
            exito=False,
            detalle_error=str(exc)[:2000],
        )
        logger.exception("Publicación del dashboard táctico de %s falló", modulo)
        return None
    pub = await repo.registrar_publicacion(
        tipo_dashboard="tactico", modulo_id=modulo_id, exito=True
    )
    for kpi in kpis:
        await repo.agregar_kpi(publicacion_id=pub.publicacion_id, **kpi)
    return pub.publicacion_id


async def ejecutar(session: AsyncSession, *, modulos: list[str] | None = None) -> dict:
    repo = TiDashboardsRepository(session)
    objetivo = [m for m in (modulos or MODULOS_TACTICOS) if m in MODULOS_TACTICOS]
    resultado: dict[str, int] = {}
    for modulo in objetivo:
        pub_id = await _publicar_uno(session, repo, modulo)
        if pub_id is not None:
            resultado[modulo] = pub_id
    await repo.flush()
    return {
        "job": NOMBRE,
        "modulos_publicados": list(resultado),
        "publicacion_id": next(iter(resultado.values()), None),
    }


async def run(session_factory: async_sessionmaker) -> dict:
    async with session_factory() as session:
        resultado = await ejecutar(session)
        await session.commit()
    logger.info("Job %s: %s", NOMBRE, resultado)
    return resultado
