"""Job diario: genera los eventos de cumpleaños / aniversario de registro del día
y dispara el cupón de hito por correo (FR-012, FR-013).

`ejecutar(session)` corre sobre una sesión dada; `run(session_factory)` abre la
suya y hace commit (scheduler periódico). La lógica vive en
`ClientesService.generar_eventos_hito` (US4).
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("sira.jobs.hitos")

NOMBRE = "eventos_hito_diario"


async def ejecutar(session: AsyncSession) -> dict:
    from src.modules.clientes.repository import ClientesRepository
    from src.modules.clientes.service import ClientesService

    svc = ClientesService(ClientesRepository(session))
    return await svc.generar_eventos_hito()


async def run(session_factory: async_sessionmaker) -> dict:
    async with session_factory() as session:
        resultado = await ejecutar(session)
        await session.commit()
    logger.info("Job %s: %s", NOMBRE, resultado)
    return resultado
