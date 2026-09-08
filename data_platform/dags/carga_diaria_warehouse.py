"""DAG `carga_diaria_warehouse` — carga diaria automática del operativo hacia el
warehouse (feature 010, US2, FR-002).

Un task por entidad `activa` de `modelo_datos_warehouse` (research.md Decisión 1):
cada task abre y cierra su propia fila de `corrida_carga` vía
`dags_utils.pipeline.correr_carga`, de modo que una entidad puede reprocesarse
sola sin arrastrar a las demás (FR-004). El índice único parcial de PostgreSQL
garantiza que dos ejecuciones solapadas no corran la misma entidad a la vez
(FR-005) — sin lock distribuido aparte.

Airflow sólo se instala dentro del contenedor `airflow` (perfil `data` de
docker-compose). Este import perezoso deja el módulo importable en tests sin
Airflow (los tests ejercitan `dags_utils/*` directamente).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

_PG_DSN = os.environ.get("SIRA_PG_DSN", "postgresql://sira:sira@postgres:5432/sira")
_CH_URL = os.environ.get("SIRA_CLICKHOUSE_URL", "")
_MINIO_ENDPOINT = os.environ.get("SIRA_MINIO_ENDPOINT", "minio:9000")
_MINIO_KEY = os.environ.get("SIRA_MINIO_ACCESS_KEY", "minioadmin")
_MINIO_SECRET = os.environ.get("SIRA_MINIO_SECRET_KEY", "minioadmin")
_BUCKET_LANDING = os.environ.get("SIRA_MINIO_BUCKET_LANDING", "landing-zone")


def _async_engine():
    # `sessionmaker(class_=AsyncSession)` en vez de `async_sessionmaker`: sirve en
    # SQLAlchemy 1.4 (la que fija Airflow 2.9) y en 2.0 (la del backend).
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    url = _PG_DSN.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(url, pool_pre_ping=True)
    return engine, sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _minio_client():
    if not _MINIO_ENDPOINT:
        return None
    from minio import Minio

    return Minio(
        _MINIO_ENDPOINT, access_key=_MINIO_KEY, secret_key=_MINIO_SECRET, secure=False
    )


def _ch_client():
    if not _CH_URL:
        return None
    import clickhouse_connect

    return _ClickHouseAdapter(clickhouse_connect.get_client(dsn=_CH_URL))


class _ClickHouseAdapter:
    """Adapta `clickhouse_connect` a la interfaz que esperan los dags_utils
    (`insert(tabla, filas)` / `command(sql)`)."""

    def __init__(self, client) -> None:
        self._c = client

    def insert(self, tabla: str, filas: list[dict]) -> None:
        if not filas:
            return
        columnas = list(filas[0].keys())
        datos = [[f.get(c) for c in columnas] for f in filas]
        self._c.insert(f"sira_warehouse.{tabla}", datos, column_names=columnas)

    def command(self, sql: str) -> None:
        self._c.command(sql)


async def _cargar_entidad(entidad_id: int, nombre_entidad: str) -> dict:
    """Todo dentro de una sola corrutina (un único `asyncio.run` por task) —
    incluida la disposición del engine, para no dejar conexiones asyncpg atadas
    a un event loop ya cerrado."""
    from dags_utils import pipeline

    engine, Session = _async_engine()
    minio, ch = _minio_client(), _ch_client()
    claves: dict = {}
    try:
        async with Session() as session:
            if ch is not None and nombre_entidad == "fact_venta":
                claves = await _claves_dimension(session)
            res = await pipeline.correr_carga(
                session,
                entidad_id=entidad_id,
                nombre_entidad=nombre_entidad,
                cliente_minio=minio,
                bucket_landing=_BUCKET_LANDING,
                cliente_ch=ch,
                claves_validas=claves,
            )
            await session.commit()
        return res.__dict__
    finally:
        await engine.dispose()


async def _entidades_activas() -> list[dict]:
    from sqlalchemy import text

    engine, Session = _async_engine()
    try:
        async with Session() as s:
            rows = await s.execute(
                text(
                    "SELECT entidad_id, nombre_entidad FROM modelo_datos_warehouse "
                    "WHERE activa = true ORDER BY entidad_id"
                )
            )
            return [dict(r._mapping) for r in rows]
    finally:
        await engine.dispose()


async def _claves_dimension(session) -> dict[str, set]:
    from sqlalchemy import text

    prod = await session.execute(text("SELECT product_id FROM productos"))
    tienda = await session.execute(text("SELECT tienda_id FROM tiendas"))
    return {
        "dim_producto": {r[0] for r in prod},
        "dim_tienda": {r[0] for r in tienda},
    }


def _build_dag():
    import asyncio

    from airflow.decorators import dag, task

    @dag(
        dag_id="carga_diaria_warehouse",
        schedule="0 2 * * *",  # diaria, 02:00 UTC
        start_date=datetime(2026, 1, 1, tzinfo=UTC),
        catchup=False,
        default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
        tags=["sira", "elt", "feature-010"],
    )
    def carga_diaria_warehouse():
        @task
        def entidades_activas() -> list[dict]:
            return asyncio.run(_entidades_activas())

        @task
        def cargar(entidad: dict) -> dict:
            return asyncio.run(
                _cargar_entidad(entidad["entidad_id"], entidad["nombre_entidad"])
            )

        cargar.expand(entidad=entidades_activas())

    return carga_diaria_warehouse()


try:  # pragma: no cover - sólo dentro del contenedor Airflow
    dag = _build_dag()
except Exception:  # noqa: BLE001 - Airflow ausente en tests / entorno backend
    dag = None
