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
            # Re-ejecutable: el job de reposición pone `cantidad_minima = 0` para
            # productos sin ventas recientes (dataset histórico). Se restaura el
            # umbral operativo para que la pantalla de quiebres tenga sentido.
            restauradas = await s.execute(
                text(
                    "UPDATE inventario SET cantidad_minima = 20 + (product_id % 40) "
                    "WHERE cantidad_minima = 0"
                )
            )
            await s.commit()
            log.info("  inventario ya poblado — mínimos restaurados: %s", restauradas.rowcount)
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


async def _cuadre_demo() -> None:
    """Siembra una apertura + un cuadre horario por caja (la mayoría cuadra, ~1 de
    cada 5 con un descuadre) para que las pantallas de Cuadre y el dashboard del
    Encargado tengan datos. El dataset Dunnhumby no trae cuadre de caja física."""
    from sqlalchemy import text
    from src.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as s:
        if await s.scalar(text("SELECT count(*) FROM cierre_caja")):
            log.info("  cuadres ya poblados, se omite")
            return
        # un cajero por tienda (empleado cualquiera de esa tienda)
        await s.execute(
            text("""
            WITH cj AS (
                SELECT c.caja_id, c.tienda_id,
                       (row_number() OVER (ORDER BY c.caja_id))::int AS rn,
                       (SELECT e.empleado_id FROM empleados e
                        WHERE e.tienda_id = c.tienda_id ORDER BY e.empleado_id LIMIT 1) AS emp
                FROM cajas c
            )
            INSERT INTO apertura_caja (caja_id, cajero_id, fondo_inicial, fecha_hora)
            SELECT caja_id, COALESCE(emp, 1), 50000,
                   CURRENT_TIMESTAMP - interval '6 hours'
            FROM cj WHERE emp IS NOT NULL
        """)
        )
        await s.execute(
            text("""
            WITH cj AS (
                SELECT c.caja_id, c.tienda_id,
                       (row_number() OVER (ORDER BY c.caja_id))::int AS rn,
                       (SELECT e.empleado_id FROM empleados e
                        WHERE e.tienda_id = c.tienda_id ORDER BY e.empleado_id LIMIT 1) AS emp
                FROM cajas c
            )
            INSERT INTO cierre_caja
                (caja_id, cajero_id, total_esperado, total_registrado, fecha_hora)
            SELECT caja_id, COALESCE(emp, 1),
                   esperado,
                   esperado + CASE WHEN rn % 5 = 0 THEN (rn % 3 - 1) * 1200 ELSE 0 END,
                   CURRENT_TIMESTAMP - interval '30 minutes'
            FROM (
                SELECT caja_id, emp, rn,
                       50000 + (abs(hashtext(caja_id::text)) % 900) * 1000 AS esperado
                FROM cj WHERE emp IS NOT NULL
            ) x
        """)
        )
        await s.commit()
        n = await s.scalar(text("SELECT count(*) FROM cierre_caja"))
        d = await s.scalar(text("SELECT count(*) FROM cierre_caja WHERE diferencia <> 0"))
        log.info("  cuadres: %s (%s con descuadre)", n, d)


_PROTOCOLO_PASOS = (
    "Protocolo de escalamiento ante fraude confirmado.\n\n"
    "1. Documentar la evidencia (cuadres, ajustes, testimonios) sin alterar registros.\n"
    "2. Notificar al Jefe de Finanzas dentro del turno.\n"
    "3. Aplicar las acciones de contención del caso (rotación de caja, resguardo de valores).\n"
    "4. Registrar el resultado sin acusar al empleado si la investigación no lo confirma."
)
_PROTOCOLO_V1 = _PROTOCOLO_PASOS
_PROTOCOLO_V2 = (
    _PROTOCOLO_PASOS + "\n5. Adjuntar respaldo de CCTV cuando exista y conservarlo 90 días."
)
_POLITICA_BASE = (
    "Política de seguridad de pagos de la red.\n\n"
    "- Sólo se ofrecen en caja los medios de pago aprobados por el Jefe de TI.\n"
    "- Los datáfonos deben cumplir la versión mínima de firmware vigente; los no "
    "conformes se marcan y se coordina su actualización o reemplazo.\n"
    "- Todo incidente de seguridad de pago se registra y se investiga hasta cerrarse.\n"
    "- El comprobante al cliente enmascara el número de tarjeta (sólo últimos 4 dígitos)."
)
_POLITICA_V1 = _POLITICA_BASE
_POLITICA_V2 = _POLITICA_BASE + "\n- Cierre de sesión de caja tras 15 minutos de inactividad."


async def _seguridad_pagos_demo() -> None:
    """Siembra el protocolo de escalamiento y la política de seguridad de pagos
    (documentos de referencia versionados) más unos incidentes de fraude de
    ejemplo en distintos estados del ciclo — el dataset no los trae."""
    from sqlalchemy import text
    from src.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as s:
        if await s.scalar(text("SELECT count(*) FROM protocolo_escalamiento")):
            log.info("  protocolo/política ya poblados, se omite")
            return
        emp = await s.scalar(text("SELECT empleado_id FROM empleados ORDER BY empleado_id LIMIT 1"))
        jefe = await s.scalar(
            text("SELECT empleado_id FROM empleados ORDER BY empleado_id DESC LIMIT 1")
        )
        for txt in (_PROTOCOLO_V1, _PROTOCOLO_V2):
            await s.execute(
                text(
                    "INSERT INTO protocolo_escalamiento (texto, definido_por, fecha_creacion) "
                    "VALUES (:t, :e, CURRENT_TIMESTAMP - make_interval(days => :d))"
                ),
                {"t": txt, "e": emp, "d": 40 if txt == _PROTOCOLO_V1 else 6},
            )
        for txt in (_POLITICA_V1, _POLITICA_V2):
            await s.execute(
                text(
                    "INSERT INTO politica_seguridad_pagos (texto, definido_por, fecha_creacion) "
                    "VALUES (:t, :e, CURRENT_TIMESTAMP - make_interval(days => :d))"
                ),
                {"t": txt, "e": emp, "d": 30 if txt == _POLITICA_V1 else 4},
            )
        # incidentes de fraude en distintos estados (origen "directo" — no hay cuadres sembrados)
        empleados = (
            (
                await s.execute(
                    text("SELECT empleado_id FROM empleados ORDER BY empleado_id OFFSET 3 LIMIT 3")
                )
            )
            .scalars()
            .all()
        )
        if len(empleados) == 3:
            await s.execute(
                text("""
                INSERT INTO incidentes_fraude
                    (empleado_id, descripcion, estado, acciones_tomadas, resultado,
                     actualizado_por, fecha_actualizacion, fecha_hora)
                VALUES
                    (:e1, 'Diferencias de arqueo repetidas a la baja en 3 turnos consecutivos.',
                     'abierto', NULL, NULL, NULL, NULL, CURRENT_TIMESTAMP - interval '2 days'),
                    (:e2, 'Anulaciones fuera de patrón tras el cierre de caja.',
                     'en_revision', 'Se revisó el CCTV del turno y se entrevistó al cajero.',
                     NULL, :jefe, CURRENT_TIMESTAMP - interval '1 day',
                     CURRENT_TIMESTAMP - interval '6 days'),
                    (:e3, 'Faltante puntual atribuido a error de conteo en billetes de $10.000.',
                     'cerrado', 'Recuento completo con doble validación.', 'descartado',
                     :jefe, CURRENT_TIMESTAMP - interval '9 days',
                     CURRENT_TIMESTAMP - interval '12 days')
            """),
                {"e1": empleados[0], "e2": empleados[1], "e3": empleados[2], "jefe": jefe},
            )
        await s.commit()
        ni = await s.scalar(text("SELECT count(*) FROM incidentes_fraude"))
        log.info("  protocolo: 2 versiones · política: 2 versiones · incidentes de fraude: %s", ni)


async def _compras_demo() -> None:
    """Da variedad al ciclo de órdenes de compra: frecuencias pactadas por
    proveedor y órdenes en cada estado (pendiente, aprobada, confirmada por el
    proveedor, rechazada) — el dataset sólo trae 6 aprobadas iguales."""
    from sqlalchemy import text
    from src.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as s:
        # frecuencias pactadas (FR-028) para los primeros proveedores
        await s.execute(
            text("""
            UPDATE proveedores SET frecuencia_reposicion = sub.frec
            FROM (
                SELECT proveedor_id,
                       (ARRAY['semanal','mensual','trimestral','semanal'])[
                           1 + (row_number() OVER (ORDER BY proveedor_id) - 1) % 4
                       ] AS frec
                FROM proveedores
            ) sub
            WHERE proveedores.proveedor_id = sub.proveedor_id
              AND proveedores.frecuencia_reposicion IS NULL
        """)
        )
        ordenes = (
            (await s.execute(text("SELECT orden_id FROM ordenes_compra ORDER BY orden_id")))
            .scalars()
            .all()
        )
        emp = await s.scalar(text("SELECT empleado_id FROM empleados ORDER BY empleado_id LIMIT 1"))
        if len(ordenes) >= 4 and emp is not None:
            # una confirmada por el proveedor, una rechazada, una vuelve a pendiente
            await s.execute(
                text("""
                UPDATE ordenes_compra
                SET estado = 'confirmada', proveedor_confirmo = true,
                    canal_respuesta = 'whatsapp',
                    respuesta_proveedor = 'Proveedor confirma despacho completo para el jueves.',
                    fecha_respuesta = CURRENT_TIMESTAMP - interval '1 day',
                    empleado_respuesta_id = :emp
                WHERE orden_id = :o
            """),
                {"o": ordenes[0], "emp": emp},
            )
            await s.execute(
                text("""
                UPDATE ordenes_compra
                SET estado = 'rechazada', proveedor_confirmo = false,
                    canal_respuesta = 'correo',
                    respuesta_proveedor = 'Sin stock hasta el próximo mes; sugiere traslado.',
                    fecha_respuesta = CURRENT_TIMESTAMP - interval '2 days',
                    empleado_respuesta_id = :emp
                WHERE orden_id = :o
            """),
                {"o": ordenes[1], "emp": emp},
            )
            await s.execute(
                text("UPDATE ordenes_compra SET estado = 'pendiente' WHERE orden_id = :o"),
                {"o": ordenes[2]},
            )
            await s.execute(
                text(
                    "UPDATE ordenes_compra SET estado = 'pendiente', tipo = 'especial', "
                    "motivo_desviacion = 'Quiebre inminente por promoción de fin de semana' "
                    "WHERE orden_id = :o"
                ),
                {"o": ordenes[3]},
            )
            # concentra las órdenes en la tienda del Encargado de demo (T01 / 1021)
            # para que su pantalla de abastecimiento tenga el ciclo completo a la vista
            tienda_demo = await s.scalar(
                text("SELECT tienda_id FROM tiendas WHERE codigo = 'T01'")
            )
            if tienda_demo is not None:
                await s.execute(
                    text("UPDATE ordenes_compra SET tienda_id = :t WHERE orden_id = ANY(:ids)"),
                    {"t": tienda_demo, "ids": list(ordenes[:4])},
                )
        await s.commit()
        estados = await s.execute(
            text("SELECT estado, count(*) FROM ordenes_compra GROUP BY estado ORDER BY estado")
        )
        log.info("  órdenes de compra: %s", [tuple(r) for r in estados])


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

    log.info("4c/5 · protocolo + política de seguridad + incidentes de fraude de demo")
    await _seguridad_pagos_demo()

    log.info("4d/5 · aperturas + cuadres horarios de demo")
    await _cuadre_demo()

    log.info("4e/5 · frecuencias de proveedor + órdenes de compra en varios estados")
    await _compras_demo()

    log.info("5/5 · jobs derivados + dashboards 009")
    await _correr_jobs()

    log.info("listo — abrí http://localhost:5173/auth/login")


if __name__ == "__main__":
    asyncio.run(main())
