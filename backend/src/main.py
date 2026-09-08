"""Entrypoint FastAPI de SIRA.

Monta los routers por módulo de negocio bajo `/api` y arranca el scheduler de
jobs periódicos (feature 002) en el ciclo de vida de la app.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.core.config import settings
from src.core.database import engine
from src.jobs import scheduler
from src.shared.exceptions import configure_logging, logger, register_exception_handlers


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logger.info("SIRA API arrancando (env=%s)", settings.app_env)
    scheduler.start()
    yield
    scheduler.stop()
    await engine.dispose()


app = FastAPI(
    title="SIRA — Sistema Inteligente de Retail Adaptativo", version="0.2.0", lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

api = APIRouter(prefix="/api")


@api.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok"}


# --- Routers por módulo ---
from src.modules.caja.router import router as caja_router  # noqa: E402
from src.modules.catalogo.router import router as catalogo_router  # noqa: E402
from src.modules.clientes.router import router as clientes_router  # noqa: E402
from src.modules.compras.router import router as compras_router  # noqa: E402
from src.modules.direccion.router import router as direccion_router  # noqa: E402
from src.modules.forecasting.router import router as forecasting_router  # noqa: E402
from src.modules.inventario.router import router as inventario_router  # noqa: E402
from src.modules.plataforma_datos.router import router as plataforma_datos_router  # noqa: E402
from src.modules.pricing.router import router as pricing_router  # noqa: E402
from src.modules.promociones.router import router as promociones_router  # noqa: E402
from src.modules.rrhh.router import router as rrhh_router  # noqa: E402
from src.modules.sistema.router import auth_router, sistema_router  # noqa: E402
from src.modules.ti.dashboards.router import router as ti_dashboards_router  # noqa: E402
from src.modules.traslados.router import router as traslados_router  # noqa: E402
from src.modules.ventas.router import router as ventas_router  # noqa: E402

api.include_router(ventas_router)
api.include_router(inventario_router)
api.include_router(compras_router)
api.include_router(catalogo_router)
api.include_router(clientes_router)
api.include_router(pricing_router)
api.include_router(forecasting_router)
api.include_router(promociones_router)
api.include_router(caja_router)
api.include_router(auth_router)
api.include_router(sistema_router)
api.include_router(rrhh_router)
api.include_router(traslados_router)
api.include_router(plataforma_datos_router)
api.include_router(direccion_router)
api.include_router(ti_dashboards_router)


# --- Endpoints de desarrollo (T005) — fuerzan un job periódico a mano.
#     No se registran en producción (usados por quickstart.md de la feature 002).
if settings.app_env != "production":
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.database import get_session

    dev = APIRouter(prefix="/_dev", tags=["_dev"])

    @dev.post("/jobs/{nombre}")
    async def ejecutar_job(
        nombre: str, session: Annotated[AsyncSession, Depends(get_session)]
    ) -> dict:
        try:
            return await scheduler.ejecutar_ahora(nombre, session)
        except KeyError as exc:
            raise HTTPException(404, f"Job '{nombre}' no existe") from exc

    @dev.get("/jobs")
    async def listar_jobs() -> dict:
        return {"jobs": list(scheduler.JOBS)}

    api.include_router(dev)

app.include_router(api)
