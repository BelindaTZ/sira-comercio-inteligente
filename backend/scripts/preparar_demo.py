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


async def _inventario_demo() -> None:
    """Siembra stock por tienda + lotes con vencimientos variados + algunas
    alertas — el dataset Dunnhumby no trae inventario (nace de operar 001)."""
    from sqlalchemy import text
    from src.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as s:
        if await s.scalar(text("SELECT count(*) FROM inventario")):
            log.info("  inventario ya poblado, se omite")
            return
        await s.execute(
            text("""
            WITH tiendas_top AS (
                SELECT tienda_id FROM tiendas WHERE codigo <> 'DEMO' ORDER BY tienda_id LIMIT 6
            ), prods AS (
                -- muestra balanceada: ~45% perecederos para que la pantalla de
                -- inventario tenga vencimientos reales, no solo abarrotes.
                (SELECT product_id, es_perecedero FROM productos
                 WHERE precio_base IS NOT NULL AND es_perecedero
                 ORDER BY product_id LIMIT 180)
                UNION ALL
                (SELECT product_id, es_perecedero FROM productos
                 WHERE precio_base IS NOT NULL AND NOT es_perecedero
                 ORDER BY product_id LIMIT 220)
            ), base AS (
                SELECT p.product_id, t.tienda_id, p.es_perecedero,
                       (5 + (p.product_id * 7 + t.tienda_id) % 260)::int AS cant
                FROM prods p CROSS JOIN tiendas_top t
            )
            INSERT INTO inventario (product_id, tienda_id, cantidad_disponible, cantidad_minima)
            SELECT product_id, tienda_id, cant, 20 + (product_id % 40) FROM base
            ON CONFLICT DO NOTHING
        """)
        )
        await s.execute(
            text("""
            INSERT INTO lotes (product_id, tienda_id, cantidad_recibida, cantidad_disponible,
                               fecha_vencimiento)
            SELECT i.product_id, i.tienda_id, i.cantidad_disponible, i.cantidad_disponible,
                   CASE WHEN p.es_perecedero
                        THEN CURRENT_DATE + ((i.product_id * 3 + i.tienda_id) % 40 - 6)
                        ELSE NULL END
            FROM inventario i JOIN productos p ON p.product_id = i.product_id
        """)
        )
        # alertas: reposición para stock < mínimo, vencimiento para lotes < 7 días
        await s.execute(
            text("""
            INSERT INTO alertas_inventario (tipo, product_id, tienda_id, estado)
            SELECT 'reposicion', product_id, tienda_id, 'pendiente'
            FROM inventario WHERE cantidad_disponible < cantidad_minima
        """)
        )
        await s.execute(
            text("""
            INSERT INTO alertas_inventario (tipo, product_id, tienda_id, lote_id, estado)
            SELECT 'vencimiento', l.product_id, l.tienda_id, l.lote_id, 'pendiente'
            FROM lotes l
            WHERE l.fecha_vencimiento IS NOT NULL
              AND l.fecha_vencimiento <= CURRENT_DATE + 7
        """)
        )
        await s.commit()
        n = await s.scalar(text("SELECT count(*) FROM inventario"))
        a = await s.scalar(text("SELECT count(*) FROM alertas_inventario"))
        log.info("  inventario: %s filas · alertas: %s", n, a)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    log.info("1/4 · cuentas de login por rol")
    from scripts.seed_usuarios_demo import seed as seed_usuarios

    await seed_usuarios(reset_password=True)

    log.info("2/5 · enriquecimiento genérico del catálogo (nombre/marca/precio/proveedores)")
    from scripts.enriquecer_catalogo import main as enriquecer

    await enriquecer()

    log.info("2b/5 · enriquecimiento del CRM (identidad chilena sintética + CLV)")
    from scripts.enriquecer_crm import main as enriquecer_crm

    await enriquecer_crm()

    log.info("3/5 · precios de competencia sintéticos")
    from scripts.seed_precio_competencia_sintetico import main as seed_competencia

    await seed_competencia()

    log.info("4/5 · inventario + lotes + alertas de demo")
    await _inventario_demo()
    # los lotes recién creados también necesitan código de proveedor
    await enriquecer()

    log.info("5/5 · jobs derivados + dashboards 009")
    await _correr_jobs()

    log.info("listo — abrí http://localhost:5173/auth/login")


if __name__ == "__main__":
    asyncio.run(main())
