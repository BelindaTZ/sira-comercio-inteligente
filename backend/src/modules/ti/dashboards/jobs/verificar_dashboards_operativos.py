"""Job diario: verifica la disponibilidad de los dashboards operativos de tienda
ya construidos dentro de cada feature 001-007 (feature 009, US3,
FR-006/FR-007/FR-008).

Sólo lectura (`SELECT MAX(fecha_hora)` por tienda) sobre las tablas fuente — no
toca ninguna feature existente (research.md Decisión 3). Inserta una fila en
`registro_publicacion_dashboard` (`tipo='operativo'`) y una fila en
`dashboard_operativo_estado` por cada (tienda × dashboard operativo).
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.ti.dashboards.repository import TiDashboardsRepository
from src.shared.dashboards import estado_operativo

logger = logging.getLogger("sira.jobs.verificar_dashboards_operativos")

NOMBRE = "verificar_dashboards_operativos_diario"


async def ejecutar(session: AsyncSession) -> dict:
    repo = TiDashboardsRepository(session)
    try:
        filas = await estado_operativo(session)
    except Exception as exc:  # noqa: BLE001 - la corrida fallida también se registra (FR-008)
        pub = await repo.registrar_publicacion(
            tipo_dashboard="operativo", exito=False, detalle_error=str(exc)[:2000]
        )
        logger.exception("Verificación de dashboards operativos falló")
        return {"job": NOMBRE, "publicacion_id": pub.publicacion_id, "exito": False}

    pub = await repo.registrar_publicacion(tipo_dashboard="operativo", exito=True)
    for fila in filas:
        await repo.agregar_estado_operativo(publicacion_id=pub.publicacion_id, **fila)
    await repo.flush()
    no_disponibles = sum(1 for f in filas if not f["disponible"])
    return {
        "job": NOMBRE,
        "publicacion_id": pub.publicacion_id,
        "exito": True,
        "verificados": len(filas),
        "no_disponibles": no_disponibles,
    }


async def run(session_factory: async_sessionmaker) -> dict:
    async with session_factory() as session:
        resultado = await ejecutar(session)
        await session.commit()
    logger.info("Job %s: %s", NOMBRE, resultado)
    return resultado
