"""Scheduler de jobs periódicos embebido en el backend (APScheduler, research.md §3).

Dos jobs para la feature 002:
  - `clv_churn_semanal`   — lunes 03:00 (recalcula CLV y churn de clientes elegibles)
  - `eventos_hito_diario` — todos los días 06:00 (cumpleaños / aniversario + cupón)

No usa Airflow (Principio III lo reserva para el ELT táctico/estratégico de 009/010).
El scheduler arranca y se apaga con el ciclo de vida de FastAPI. Cada job abre su
propia sesión de BD y hace su propio `commit`.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.core.config import settings
from src.core.database import AsyncSessionLocal
from src.jobs import (
    calcular_afinidad_job,
    calcular_alertas_competencia_job,
    calcular_clv_churn_job,
    clasificar_abc_job,
    entrenar_modelo_demanda_job,
    eventos_hito_job,
    generar_candidatos_liquidacion_job,
    generar_propuestas_ajuste_job,
    monitorear_precision_job,
)

logger = logging.getLogger("sira.jobs")

_scheduler: AsyncIOScheduler | None = None

# nombre → módulo del job. `.run(session_factory)` para el scheduler periódico;
# `.ejecutar(session)` para el endpoint de desarrollo (usa la sesión del request).
JOBS = {
    calcular_clv_churn_job.NOMBRE: calcular_clv_churn_job,
    eventos_hito_job.NOMBRE: eventos_hito_job,
    generar_propuestas_ajuste_job.NOMBRE: generar_propuestas_ajuste_job,
    calcular_alertas_competencia_job.NOMBRE: calcular_alertas_competencia_job,
    entrenar_modelo_demanda_job.NOMBRE: entrenar_modelo_demanda_job,
    monitorear_precision_job.NOMBRE: monitorear_precision_job,
    calcular_afinidad_job.NOMBRE: calcular_afinidad_job,
    clasificar_abc_job.NOMBRE: clasificar_abc_job,
    generar_candidatos_liquidacion_job.NOMBRE: generar_candidatos_liquidacion_job,
}


async def _run(nombre: str) -> dict:
    try:
        return await JOBS[nombre].run(AsyncSessionLocal)
    except Exception:  # noqa: BLE001 - un job no debe tumbar el scheduler
        logger.exception("Job %s falló", nombre)
        return {"job": nombre, "error": True}


async def ejecutar_ahora(nombre: str, session) -> dict:
    """Fuerza la ejecución inmediata de un job sobre la sesión dada (endpoint de
    desarrollo / quickstart). El caller decide si hace commit."""
    if nombre not in JOBS:
        raise KeyError(nombre)
    return await JOBS[nombre].ejecutar(session)


def start() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    # Los jobs periódicos sólo se activan fuera de los tests.
    if settings.app_env == "test":
        logger.info("Scheduler no arranca en entorno de test")
        return

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _run,
        CronTrigger(day_of_week="mon", hour=3, minute=0),
        args=[calcular_clv_churn_job.NOMBRE],
        id=calcular_clv_churn_job.NOMBRE,
        replace_existing=True,
    )
    _scheduler.add_job(
        _run,
        CronTrigger(hour=6, minute=0),
        args=[eventos_hito_job.NOMBRE],
        id=eventos_hito_job.NOMBRE,
        replace_existing=True,
    )
    # Feature 003: propuestas de ajuste (lunes 04:00) y alertas de competencia (lunes 05:00).
    _scheduler.add_job(
        _run,
        CronTrigger(day_of_week="mon", hour=4, minute=0),
        args=[generar_propuestas_ajuste_job.NOMBRE],
        id=generar_propuestas_ajuste_job.NOMBRE,
        replace_existing=True,
    )
    _scheduler.add_job(
        _run,
        CronTrigger(day_of_week="mon", hour=5, minute=0),
        args=[calcular_alertas_competencia_job.NOMBRE],
        id=calcular_alertas_competencia_job.NOMBRE,
        replace_existing=True,
    )
    # Feature 004: entrenamiento mensual (día 1, 02:00) y monitoreo semanal (lunes 05:30).
    _scheduler.add_job(
        _run,
        CronTrigger(day=1, hour=2, minute=0),
        args=[entrenar_modelo_demanda_job.NOMBRE],
        id=entrenar_modelo_demanda_job.NOMBRE,
        replace_existing=True,
    )
    _scheduler.add_job(
        _run,
        CronTrigger(day_of_week="mon", hour=5, minute=30),
        args=[monitorear_precision_job.NOMBRE],
        id=monitorear_precision_job.NOMBRE,
        replace_existing=True,
    )
    # Feature 005: afinidad (día 1, 03:00) + ABC (día 1, 03:30) mensuales; candidatos (lunes 06:00).
    _scheduler.add_job(
        _run,
        CronTrigger(day=1, hour=3, minute=0),
        args=[calcular_afinidad_job.NOMBRE],
        id=calcular_afinidad_job.NOMBRE,
        replace_existing=True,
    )
    _scheduler.add_job(
        _run,
        CronTrigger(day=1, hour=3, minute=30),
        args=[clasificar_abc_job.NOMBRE],
        id=clasificar_abc_job.NOMBRE,
        replace_existing=True,
    )
    _scheduler.add_job(
        _run,
        CronTrigger(day_of_week="mon", hour=6, minute=0),
        args=[generar_candidatos_liquidacion_job.NOMBRE],
        id=generar_candidatos_liquidacion_job.NOMBRE,
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler arrancado con jobs: %s", list(JOBS))


def stop() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
