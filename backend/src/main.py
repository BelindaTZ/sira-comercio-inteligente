"""Entrypoint FastAPI de SIRA (T015).

Monta los routers por módulo de negocio bajo `/api`. Cada módulo
(ventas, inventario, catalogo, compras) registra su router en su propia fase de
`tasks.md`; aquí solo queda el punto de montaje y lo transversal (CORS,
manejo de errores, logging, healthcheck).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.core.config import settings
from src.core.database import engine
from src.shared.exceptions import configure_logging, logger, register_exception_handlers


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logger.info("SIRA API arrancando (env=%s)", settings.app_env)
    yield
    await engine.dispose()


app = FastAPI(
    title="SIRA — Core de Ventas e Inventario",
    version="0.1.0",
    lifespan=lifespan,
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


# --- Routers por módulo (se activan en sus fases respectivas) ---
from src.modules.catalogo.router import router as catalogo_router  # noqa: E402
from src.modules.compras.router import router as compras_router  # noqa: E402
from src.modules.inventario.router import router as inventario_router  # noqa: E402
from src.modules.ventas.router import router as ventas_router  # noqa: E402

api.include_router(ventas_router)
api.include_router(inventario_router)
api.include_router(compras_router)
api.include_router(catalogo_router)

app.include_router(api)
