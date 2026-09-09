"""Consultas de la pantalla "Gestión de Clientes & Programa de Lealtad" (CRM).

Sólo lectura y agregación — el directorio enriquecido (LTV, frecuencia, puntos,
sucursal habitual), la ficha 360° del cliente y los KPIs de la cabecera.

El histórico Dunnhumby está en dólares del dataset; se muestra en CLP con un
factor fijo (`_CLP`, mismo criterio que el enriquecimiento del catálogo). Los
puntos "Club Marzú" se derivan del gasto: ~1 punto por cada `_PTS_DIV` pesos
gastados (saldo vigente).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_CLP = 950
_PTS_DIV = 1000
_CONFIRMADA = "v.estado = 'confirmada'"


class DirectorioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def directorio(
        self, *, search, nivel_id, activo, offset, limit
    ) -> tuple[list[dict], int]:
        binds: dict = {"offset": offset, "limit": limit}
        filtros = ["1=1"]
        if search:
            filtros.append(
                "(c.nombre ILIKE :q OR c.email ILIKE :q "
                "OR c.documento_identidad ILIKE :q OR c.telefono ILIKE :q)"
            )
            binds["q"] = f"%{search}%"
        if activo is not None:
            filtros.append("c.activo = :activo")
            binds["activo"] = activo
        if nivel_id is not None:
            filtros.append("clv.nivel_id = :nivel")
            binds["nivel"] = nivel_id
        where = " AND ".join(filtros)
        # CTEs pre-agregadas UNA vez (no un LATERAL por cliente): el histórico de
        # ventas se agrupa por household en una sola pasada.
        ctes = f"""
            WITH clv AS (
                SELECT DISTINCT ON (household_id) household_id, clv_score, nivel_id
                FROM cliente_clv ORDER BY household_id, fecha_calculo DESC
            ), ch AS (
                SELECT DISTINCT ON (household_id) household_id, severidad
                FROM churn_score ORDER BY household_id, fecha_calculo DESC
            ), vg AS (
                SELECT v.household_id,
                       count(*) AS tickets,
                       max(v.fecha_hora)::date AS ultima_compra,
                       (array_agg(v.venta_id ORDER BY v.fecha_hora DESC))[1] AS ultimo_ticket,
                       round(sum(v.total) * {_CLP}) AS ltv,
                       round(sum(v.total) * {_CLP} / {_PTS_DIV}) AS puntos,
                       round((count(*)::numeric / GREATEST(1,
                         (max(v.fecha_hora)::date - min(v.fecha_hora)::date) / 7.0))::numeric,
                         1) AS frecuencia_sem
                FROM ventas v
                WHERE v.household_id IS NOT NULL AND {_CONFIRMADA}
                GROUP BY v.household_id
            ), sh AS (
                SELECT DISTINCT ON (v.household_id) v.household_id, t.nombre AS sucursal
                FROM ventas v JOIN tiendas t ON t.tienda_id = v.tienda_id
                WHERE v.household_id IS NOT NULL AND {_CONFIRMADA}
                GROUP BY v.household_id, t.nombre
                ORDER BY v.household_id, count(*) DESC
            )
        """
        total = await self.session.scalar(
            text(f"""
            {ctes}
            SELECT count(*) FROM clientes c
            LEFT JOIN clv ON clv.household_id = c.household_id
            WHERE {where}
            """),
            binds,
        )
        rows = (
            await self.session.execute(
                text(f"""
                {ctes}
                SELECT c.household_id, c.nombre, c.documento_identidad, c.email,
                       c.telefono, c.activo,
                       clv.clv_score, clv.nivel_id, n.nombre AS nivel_nombre,
                       ch.severidad AS severidad_churn,
                       COALESCE(vg.tickets, 0) AS tickets,
                       vg.ultima_compra, vg.ultimo_ticket,
                       COALESCE(vg.ltv, 0) AS ltv,
                       COALESCE(vg.puntos, 0) AS puntos,
                       COALESCE(vg.frecuencia_sem, 0) AS frecuencia_sem,
                       sh.sucursal
                FROM clientes c
                LEFT JOIN clv ON clv.household_id = c.household_id
                LEFT JOIN ch ON ch.household_id = c.household_id
                LEFT JOIN niveles_fidelizacion n ON n.nivel_id = clv.nivel_id
                LEFT JOIN vg ON vg.household_id = c.household_id
                LEFT JOIN sh ON sh.household_id = c.household_id
                WHERE {where}
                ORDER BY vg.ltv DESC NULLS LAST, c.household_id
                OFFSET :offset LIMIT :limit
                """),
                binds,
            )
        ).mappings()
        return [dict(r) for r in rows], int(total or 0)

    async def ficha_360(self, household_id: int) -> dict:
        cab = (
            await self.session.execute(
                text(f"""
                SELECT round(COALESCE(sum(total), 0) * {_CLP} / {_PTS_DIV}) AS puntos,
                       round(COALESCE(sum(total), 0) * {_CLP}) AS ltv,
                       count(*) AS tickets
                FROM ventas v WHERE v.household_id = :h AND {_CONFIRMADA}
                """),
                {"h": household_id},
            )
        ).mappings().first()
        cupones = (
            await self.session.execute(
                text("""
                SELECT DISTINCT ON (cu.coupon_upc)
                       cu.coupon_upc, p.nombre AS producto,
                       p.product_category AS categoria, ca.end_date
                FROM campana_cliente cc
                JOIN cupones cu ON cu.campaign_id = cc.campaign_id
                JOIN campanas ca ON ca.campaign_id = cc.campaign_id
                JOIN productos p ON p.product_id = cu.product_id
                WHERE cc.household_id = :h
                  AND NOT EXISTS (SELECT 1 FROM cupon_redimido r
                                  WHERE r.household_id = cc.household_id
                                    AND r.coupon_upc = cu.coupon_upc)
                ORDER BY cu.coupon_upc, ca.end_date DESC
                LIMIT 6
                """),
                {"h": household_id},
            )
        ).mappings().all()
        consumo = (
            await self.session.execute(
                text(f"""
                SELECT p.product_category AS categoria,
                       round(sum(vd.sales_value * vd.cantidad)::numeric, 2) AS monto
                FROM venta_detalle vd
                JOIN ventas v ON v.venta_id = vd.venta_id
                              AND v.household_id = :h AND {_CONFIRMADA}
                JOIN productos p ON p.product_id = vd.product_id
                WHERE p.product_category IS NOT NULL
                GROUP BY p.product_category ORDER BY monto DESC LIMIT 4
                """),
                {"h": household_id},
            )
        ).mappings().all()
        compras = (
            await self.session.execute(
                text(f"""
                SELECT v.venta_id, v.fecha_hora, t.nombre AS tienda,
                       round(v.total * {_CLP}) AS total,
                       round(v.total * {_CLP} / {_PTS_DIV}) AS puntos,
                       (SELECT count(*) FROM venta_detalle d
                          WHERE d.venta_id = v.venta_id) AS items
                FROM ventas v JOIN tiendas t ON t.tienda_id = v.tienda_id
                WHERE v.household_id = :h AND {_CONFIRMADA}
                ORDER BY v.fecha_hora DESC LIMIT 3
                """),
                {"h": household_id},
            )
        ).mappings().all()
        return {
            "puntos": int(cab["puntos"]) if cab and cab["puntos"] else 0,
            "ltv": float(cab["ltv"]) if cab and cab["ltv"] else 0.0,
            "tickets": int(cab["tickets"]) if cab else 0,
            "cupones": [dict(r) for r in cupones],
            "consumo": [dict(r) for r in consumo],
            "compras": [dict(r) for r in compras],
        }

    async def resumen_crm(self) -> dict:
        row = (
            await self.session.execute(
                text(f"""
                SELECT
                  (SELECT count(*) FROM clientes WHERE activo) AS base_activos,
                  -- ticket medio de los tiers altos (Oro/Platino) vs. el resto,
                  -- que es la comparación que tiene sentido con este dataset
                  -- (todos los hogares que compran tienen CLV calculado).
                  (SELECT round(avg(v.total) * {_CLP}) FROM ventas v
                     WHERE {_CONFIRMADA} AND v.household_id IN (
                       SELECT cv.household_id FROM cliente_clv cv
                        JOIN niveles_fidelizacion n ON n.nivel_id = cv.nivel_id
                        WHERE n.nombre IN ('Oro', 'Platino'))) AS ticket_club,
                  (SELECT round(avg(v.total) * {_CLP}) FROM ventas v
                     WHERE {_CONFIRMADA} AND (
                       v.household_id IS NULL OR v.household_id IN (
                         SELECT cv.household_id FROM cliente_clv cv
                          JOIN niveles_fidelizacion n ON n.nivel_id = cv.nivel_id
                          WHERE n.nombre NOT IN ('Oro', 'Platino')))) AS ticket_no_club,
                  (SELECT count(DISTINCT household_id) FROM cupon_redimido) AS redimidos,
                  (SELECT count(DISTINCT household_id) FROM campana_cliente) AS asignados,
                  (SELECT count(*) FROM cliente_clv) AS con_clv
                """)
            )
        ).mappings().first()
        return dict(row) if row else {}

    async def conteo_por_nivel(self) -> list[dict]:
        rows = (
            await self.session.execute(
                text("""
                SELECT n.nivel_id, n.nombre, n.umbral_clv_min,
                       (SELECT count(*) FROM cliente_clv cv WHERE cv.nivel_id = n.nivel_id)
                         AS clientes
                FROM niveles_fidelizacion n ORDER BY n.umbral_clv_min
                """)
            )
        ).mappings().all()
        return [dict(r) for r in rows]
