"""Lógica compartida de los dashboards multinivel (feature 009).

Una sola implementación de:
- el catálogo de KPIs estratégicos/tácticos y de dashboards operativos,
- la lectura de los valores ya calculados por otras features (Principio VIII — no
  se recalcula ningún KPI aquí),
- la regla de antigüedad de FR-007,

reutilizada por los jobs de publicación (`modules/*/jobs/`) y por las capas de
servicio de lectura. En producción las agregaciones pesadas del dashboard
estratégico/táctico las provee ClickHouse (010); sin warehouse configurado
(tests / desarrollo) se leen de PostgreSQL en modo solo lectura — mismo criterio
que el cargador no-op de `plataforma_datos` (research.md 010, Decisión 3).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# FR-007 — un dashboard operativo con más de esta antigüedad se marca no disponible.
ANTIGUEDAD_MAXIMA = timedelta(days=1)

# research.md Decisión 4 — los 6 módulos con Jefe propio y, por tanto, dashboard táctico.
ROL_A_MODULO_TACTICO: dict[str, str] = {
    "Jefe_Comercial": "Comercial",
    "Jefe_Marketing": "Marketing_CRM",
    "Jefe_Operaciones": "Operaciones",
    "Jefe_Finanzas": "Finanzas",
    "Jefe_TI": "TI",
    "Jefe_RRHH": "RRHH",
}
MODULOS_TACTICOS: tuple[str, ...] = tuple(ROL_A_MODULO_TACTICO.values())
ROL_LECTURA_GLOBAL = "Gerente_General"

# research.md Decisión 3 — nombre del dashboard operativo → tabla fuente ya
# construida dentro de su feature dueña, con su columna de fecha y de tienda.
# El job sólo hace `SELECT MAX(...)` de solo lectura sobre estas tablas (FR-006).
_FUENTES_OPERATIVAS: tuple[tuple[str, str], ...] = (
    (
        "alertas_reposicion",
        "SELECT tienda_id, MAX(fecha_generada) AS fecha FROM alertas_inventario GROUP BY tienda_id",
    ),
    (
        "cuadre_caja",
        "SELECT c.tienda_id, MAX(cc.fecha_hora) AS fecha "
        "FROM cierre_caja cc JOIN cajas c ON c.caja_id = cc.caja_id "
        "GROUP BY c.tienda_id",
    ),
    (
        "seguimiento_merma",
        "SELECT tienda_id, MAX(fecha::timestamp) AS fecha FROM mermas GROUP BY tienda_id",
    ),
)


def _kpi(dimension: str, nombre: str, valor) -> dict:
    """Normaliza un KPI: `disponible = false` + `valor = None` cuando no hay
    fuente real (Principio VII)."""
    if valor is None:
        return {"dimension": dimension, "nombre_kpi": nombre, "valor": None, "disponible": False}
    return {
        "dimension": dimension,
        "nombre_kpi": nombre,
        "valor": Decimal(str(valor)).quantize(Decimal("0.0001")),
        "disponible": True,
    }


async def _scalar(session: AsyncSession, sql: str) -> object | None:
    return await session.scalar(text(sql))


async def kpis_estrategicos(session: AsyncSession) -> list[dict]:
    """KPIs del dashboard estratégico consolidado (US1, FR-001/FR-002).

    OE-4 (Market Share/NPS) permanece sin fuente real — sin canal de encuesta a
    cliente en el alcance del proyecto (research.md Decisión 5). OE-8 sí tiene
    fuente real desde 011-recursos-humanos.
    """
    ventas_netas = await _scalar(
        session,
        "SELECT SUM(vd.sales_value) FROM venta_detalle vd "
        "JOIN ventas v ON v.venta_id = vd.venta_id WHERE v.estado = 'confirmada'",
    )
    ticket_promedio = await _scalar(
        session,
        "SELECT AVG(t.total) FROM (SELECT v.venta_id, SUM(vd.sales_value) AS total "
        "FROM ventas v JOIN venta_detalle vd ON vd.venta_id = v.venta_id "
        "WHERE v.estado = 'confirmada' GROUP BY v.venta_id) t",
    )
    merma_valorizada = await _scalar(
        session,
        "SELECT SUM(valor) FROM mermas WHERE estado_validacion = 'validada'",
    )
    clima_laboral = await _scalar(
        session,
        "SELECT AVG(resultado_promedio) FROM clima_laboral",
    )
    return [
        _kpi("OE-1", "Ventas netas de la red", ventas_netas),
        _kpi("OE-2", "Ticket promedio", ticket_promedio),
        _kpi("OE-3", "Merma valorizada", merma_valorizada),
        _kpi("OE-4", "Market Share / NPS", None),  # sin fuente real (Principio VII)
        _kpi("OE-8", "Índice de clima laboral", clima_laboral),
    ]


async def kpis_tacticos(session: AsyncSession, modulo_nombre: str) -> list[dict]:
    """KPIs del dashboard táctico de un departamento (US2, FR-004).

    Cada módulo aporta un KPI principal (de la feature dueña) y un KPI secundario
    que puede quedar `disponible = false` por datos insuficientes sin bloquear el
    resto del dashboard (Acceptance Scenario 3)."""
    consultas: dict[str, list[tuple[str, str | None]]] = {
        "Comercial": [
            (
                "Propuestas de ajuste de precio abiertas",
                "SELECT COUNT(*) FROM propuesta_ajuste_precio WHERE estado = 'pendiente'",
            ),
            ("Elasticidad de precio estimada", None),  # sin modelo entrenado en dev
        ],
        "Marketing_CRM": [
            (
                "Campañas vigentes",
                "SELECT COUNT(*) FROM campanas "
                "WHERE start_date <= CURRENT_DATE AND end_date >= CURRENT_DATE",
            ),
            ("CLV promedio de la cartera", "SELECT AVG(clv_score) FROM cliente_clv"),
        ],
        "Operaciones": [
            (
                "Órdenes de compra en curso",
                "SELECT COUNT(*) FROM ordenes_compra WHERE estado IN ('pendiente','aprobada')",
            ),
            (
                "Alertas de reposición pendientes",
                "SELECT COUNT(*) FROM alertas_inventario "
                "WHERE tipo = 'reposicion' AND estado = 'pendiente'",
            ),
        ],
        "Finanzas": [
            (
                "Cierres de caja del día",
                "SELECT COUNT(*) FROM cierre_caja WHERE fecha_hora::date = CURRENT_DATE",
            ),
            (
                "Diferencia de caja acumulada",
                "SELECT COALESCE(SUM(diferencia), 0) FROM cierre_caja",
            ),
        ],
        "TI": [
            (
                "Corridas de carga exitosas",
                "SELECT COUNT(*) FROM corrida_carga WHERE estado = 'exitosa'",
            ),
            ("Registros de calidad señalados", "SELECT COUNT(*) FROM registro_calidad_carga"),
        ],
        "RRHH": [
            ("Empleados activos", "SELECT COUNT(*) FROM empleados WHERE activo = true"),
            ("Índice de clima laboral", "SELECT AVG(resultado_promedio) FROM clima_laboral"),
        ],
    }
    filas: list[dict] = []
    for nombre, sql in consultas.get(modulo_nombre, []):
        valor = None if sql is None else await _scalar(session, sql)
        filas.append(_kpi(modulo_nombre, nombre, valor))
    return filas


async def estado_operativo(session: AsyncSession) -> list[dict]:
    """Una fila por (tienda activa × dashboard operativo) con `MAX(fecha_hora)` de
    su tabla fuente y la bandera de disponibilidad de FR-007. Solo lectura."""
    tiendas = list(
        (
            await session.execute(
                text("SELECT tienda_id FROM tiendas WHERE activa = true ORDER BY tienda_id")
            )
        ).scalars()
    )
    # Las columnas fuente son TIMESTAMP naive tratados como UTC (convención del
    # proyecto, igual que `traslados._ahora`).
    ahora = datetime.now(UTC).replace(tzinfo=None)
    filas: list[dict] = []
    for nombre_dashboard, sql in _FUENTES_OPERATIVAS:
        por_tienda = {r.tienda_id: r.fecha for r in (await session.execute(text(sql))).all()}
        for tienda_id in tiendas:
            fecha = por_tienda.get(tienda_id)
            disponible = fecha is not None and (ahora - fecha) <= ANTIGUEDAD_MAXIMA
            filas.append(
                {
                    "tienda_id": tienda_id,
                    "nombre_dashboard": nombre_dashboard,
                    "fecha_ultima_actualizacion": fecha,
                    "disponible": disponible,
                }
            )
    return filas
