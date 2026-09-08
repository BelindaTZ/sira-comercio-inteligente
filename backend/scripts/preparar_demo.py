"""Deja la BD lista para una demo completa DESPUÉS de `cargar_dataset_inicial`.

Hace, en orden y sin depender de la API levantada:

1. cuentas de login por rol (`seed_usuarios_demo`),
2. precios de competencia sintéticos (feature 003),
3. todos los jobs derivados que normalmente corren por cron (CLV/churn, afinidad,
   ABC, entrenamiento de demanda, propuestas de ajuste, alertas de competencia,
   candidatos a liquidación, eventos hito),
4. la publicación de los 3 dashboards de la feature 009 (estratégico, tácticos,
   verificación operativa).

Cada paso es idempotente o se puede repetir sin romper nada. Si un job falla, se
registra y se sigue con el resto.

Uso:
    cd backend
    .venv/Scripts/python -m scripts.cargar_dataset_inicial          # 1º: el dataset (pesado)
    .venv/Scripts/python -m scripts.preparar_demo                   # 2º: esto
"""

from __future__ import annotations

import asyncio
import logging
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

log = logging.getLogger("preparar_demo")


async def _correr_jobs() -> None:
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
    from src.modules.direccion.jobs import publicar_dashboard_estrategico
    from src.modules.ti.dashboards.jobs import (
        publicar_dashboards_tacticos,
        verificar_dashboards_operativos,
    )

    secuencia = [
        clasificar_abc_job,
        calcular_afinidad_job,
        calcular_clv_churn_job,
        entrenar_modelo_demanda_job,
        monitorear_precision_job,
        generar_propuestas_ajuste_job,
        calcular_alertas_competencia_job,
        generar_candidatos_liquidacion_job,
        eventos_hito_job,
        # feature 009 — al final, cuando el resto de KPIs ya está calculado
        verificar_dashboards_operativos,
        publicar_dashboards_tacticos,
        publicar_dashboard_estrategico,
    ]
    for job in secuencia:
        try:
            res = await job.run(AsyncSessionLocal)
            log.info("  ✓ %s → %s", job.NOMBRE, res)
        except Exception:  # noqa: BLE001 - un job no debe abortar la preparación
            log.exception("  ✗ %s falló", job.NOMBRE)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    log.info("1/3 · cuentas de login por rol")
    from scripts.seed_usuarios_demo import seed as seed_usuarios

    await seed_usuarios(reset_password=True)

    log.info("2/3 · precios de competencia sintéticos")
    from scripts.seed_precio_competencia_sintetico import main as seed_competencia

    await seed_competencia()

    log.info("3/3 · jobs derivados + dashboards 009")
    await _correr_jobs()

    log.info("listo — abrí http://localhost:5173/auth/login")


if __name__ == "__main__":
    asyncio.run(main())
