"""Deja la BD lista para una demo completa DESPUÉS de `cargar_dataset_inicial`.

Hace, en orden y sin depender de la API levantada:

1. cuentas de login por rol (`seed_usuarios_demo`),
2. enriquecimiento sintético del catálogo y del CRM + precios de competencia,
3. inventario/lotes/alertas de demo + cajas/datáfonos/estándar de seguridad,
4. todos los jobs derivados que normalmente corren por cron (CLV/churn, afinidad,
   ABC, entrenamiento de demanda, propuestas de ajuste, alertas de competencia,
   candidatos a liquidación, eventos hito),
5. la publicación de los 3 dashboards de la feature 009 (estratégico, tácticos,
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
        refrescar_catalogo_kpi_job,
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
        refrescar_catalogo_kpi_job,
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


async def _caja_demo() -> None:
    """Siembra cajas + un datáfono por caja + el estándar de seguridad de pagos
    vigente. El dataset Dunnhumby no trae infraestructura de sala (nace de operar
    001/006); sin esto las pantallas de POS, cuadre y datáfonos quedan vacías.

    NO fabrica tiempos de cobro: la medición de `fecha_inicio_cobro` (FR-015 de
    007) aplica solo a ventas registradas en vivo — Principio VII.
    """
    from sqlalchemy import text
    from src.core.database import AsyncSessionLocal

    # firmware < estándar → 'requiere_actualizacion' (comparación lexical segura:
    # todos los segmentos son de un dígito). El estándar vigente es 4.8.0; el modelo
    # y firmware de cada caja rotan por 4 valores (el 4º, v4.7.9, queda no conforme).
    ESTANDAR = "4.8.0"

    async with AsyncSessionLocal() as s:
        if await s.scalar(text("SELECT count(*) FROM cajas")):
            log.info("  cajas ya pobladas, se omite")
            return
        await s.execute(
            text("""
            WITH tiendas_op AS (
                SELECT tienda_id, row_number() OVER (ORDER BY tienda_id) AS rn
                FROM tiendas WHERE codigo <> 'DEMO'
            ), nums AS (SELECT generate_series(1, 4) AS n)
            INSERT INTO cajas (tienda_id, nombre, activa)
            SELECT t.tienda_id, 'Caja ' || lpad(n.n::text, 2, '0'), true
            FROM tiendas_op t CROSS JOIN nums n
        """)
        )
        # un datáfono por caja; el modelo/firmware rota de forma determinista
        await s.execute(
            text("""
            WITH c AS (
                SELECT caja_id,
                       (row_number() OVER (ORDER BY caja_id) - 1)::int AS idx
                FROM cajas
            ), m(modelo, orden) AS (
                VALUES ('Ingenico Move 5000', 0), ('Verifone V240m', 1),
                       ('PAX A920 Pro', 2), ('Ingenico Lane/3000', 3)
            ), f(firmware, orden) AS (
                VALUES ('4.8.2', 0), ('4.8.2', 1), ('4.8.0', 2), ('4.7.9', 3)
            )
            INSERT INTO datafonos (caja_id, modelo, version_firmware,
                                   fecha_ultima_actualizacion, estado)
            SELECT c.caja_id, m.modelo, f.firmware,
                   CURRENT_DATE - ((c.idx * 37) % 400),
                   CASE WHEN f.firmware < :estandar
                        THEN 'requiere_actualizacion' ELSE 'activo' END
            FROM c
            JOIN m ON m.orden = c.idx % 4
            JOIN f ON f.orden = c.idx % 4
        """),
            {"estandar": ESTANDAR},
        )
        await s.execute(
            text("""
            INSERT INTO configuracion_seguridad_pagos (version_minima_firmware, actualizado_por)
            SELECT :estandar, empleado_id FROM empleados ORDER BY empleado_id LIMIT 1
        """),
            {"estandar": ESTANDAR},
        )
        await s.commit()
        nc = await s.scalar(text("SELECT count(*) FROM cajas"))
        nd = await s.scalar(text("SELECT count(*) FROM datafonos"))
        nnc = await s.scalar(
            text("SELECT count(*) FROM datafonos WHERE estado = 'requiere_actualizacion'")
        )
        log.info(
            "  cajas: %s · datáfonos: %s (%s no conformes) · estándar %s", nc, nd, nnc, ESTANDAR
        )


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

    log.info("4b/5 · cajas + datáfonos + estándar de seguridad de pagos")
    await _caja_demo()

    log.info("5/5 · jobs derivados + dashboards 009")
    await _correr_jobs()

    log.info("listo — abrí http://localhost:5173/auth/login")


if __name__ == "__main__":
    asyncio.run(main())
