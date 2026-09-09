"""CatalogoRepository (T064) — acceso a datos de `productos` e `historial_precios`."""

from __future__ import annotations

from sqlalchemy import Select, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.producto import Producto
from src.models.regla_recargo_canal import ReglaRecargoCanal
from src.shared.repository import BaseRepository


class CatalogoRepository(BaseRepository[Producto]):
    model = Producto

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    def agregar(self, entity) -> None:
        self.session.add(entity)

    async def flush(self) -> None:
        await self.session.flush()

    async def refrescar(self, entity) -> None:
        await self.session.refresh(entity)

    async def get_producto(self, product_id: int) -> Producto | None:
        return await self.session.get(Producto, product_id)

    async def categorias(self) -> list[str]:
        """Valores distintos de `product_category` — no hay tabla maestra de
        categorías; nacen de los productos del catálogo."""
        rows = await self.session.execute(
            select(Producto.product_category)
            .where(Producto.product_category.isnot(None))
            .distinct()
            .order_by(Producto.product_category)
        )
        return [c for (c,) in rows]

    async def existe_barcode(self, codigo_barras: str) -> bool:
        stmt = select(Producto.product_id).where(Producto.codigo_barras == codigo_barras)
        return (await self.session.scalars(stmt)).first() is not None

    async def registrar_historial_precio(self, product_id: int, precio) -> None:
        from sqlalchemy import text

        await self.session.execute(
            text(
                "INSERT INTO historial_precios (product_id, tienda_id, precio, fecha_inicio) "
                "VALUES (:p, NULL, :precio, CURRENT_DATE)"
            ),
            {"p": product_id, "precio": precio},
        )

    def productos_query(
        self,
        *,
        search: str | None = None,
        codigo_barras: str | None = None,
        categoria: str | None = None,
        activo: bool | None = None,
    ) -> Select:
        stmt = select(Producto)
        if search:
            patron = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Producto.nombre.ilike(patron),
                    Producto.product_type.ilike(patron),
                    Producto.product_category.ilike(patron),
                )
            )
        if codigo_barras:
            stmt = stmt.where(Producto.codigo_barras == codigo_barras)
        if categoria:
            stmt = stmt.where(Producto.product_category == categoria)
        if activo is not None:
            stmt = stmt.where(Producto.activo.is_(activo))
        return stmt

    # ----------------------------------------- matriz de precios por canal (US4)
    async def listar_canales(self) -> list[ReglaRecargoCanal]:
        rows = await self.session.scalars(
            select(ReglaRecargoCanal).order_by(ReglaRecargoCanal.orden, ReglaRecargoCanal.canal)
        )
        return list(rows.all())

    async def get_canal(self, canal: str) -> ReglaRecargoCanal | None:
        return await self.session.get(ReglaRecargoCanal, canal)

    async def matriz_precios(
        self,
        *,
        search: str | None,
        categoria: str | None,
        margen: str | None,
        activo: bool | None,
        offset: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        """Fila = producto + margen real vs. objetivo de su categoría + estado.
        `margen` filtra por banda: 'bajo' (<20%), 'normal' (20-35%), 'premium' (>35%)."""
        filtros = ["1=1"]
        binds: dict = {"offset": offset, "limit": limit}
        if search:
            filtros.append(
                "(p.nombre ILIKE :q OR p.product_type ILIKE :q OR p.marca ILIKE :q "
                "OR p.codigo_barras = :qexact)"
            )
            binds["q"] = f"%{search}%"
            binds["qexact"] = search
        if categoria:
            filtros.append("p.product_category = :cat")
            binds["cat"] = categoria
        if activo is not None:
            filtros.append("p.activo = :activo")
            binds["activo"] = activo
        margen_expr = (
            "CASE WHEN p.precio_base > 0 AND p.costo IS NOT NULL "
            "THEN (p.precio_base - p.costo) / p.precio_base * 100 END"
        )
        if margen == "bajo":
            filtros.append(f"{margen_expr} < 20")
        elif margen == "normal":
            filtros.append(f"{margen_expr} BETWEEN 20 AND 35")
        elif margen == "premium":
            filtros.append(f"{margen_expr} > 35")
        where = " AND ".join(filtros)
        base = f"""
            FROM productos p
            LEFT JOIN margenes_objetivo mo ON mo.product_category = p.product_category
            WHERE {where}
        """
        total = await self.session.scalar(text(f"SELECT count(*) {base}"), binds) or 0
        rows = (
            await self.session.execute(
                text(f"""
                SELECT p.product_id, p.codigo_barras, p.nombre, p.marca,
                       p.product_category, p.product_type, p.package_size, p.imagen_url,
                       p.clasificacion_abc, p.es_ancla, p.activo,
                       p.costo, p.precio_base,
                       {margen_expr} AS margen_pct,
                       mo.margen_objetivo_pct
                {base}
                ORDER BY p.product_id DESC
                OFFSET :offset LIMIT :limit
                """),
                binds,
            )
        ).mappings()
        return [dict(r) for r in rows], int(total)

    async def resumen_catalogo(self) -> dict:
        row = (
            await self.session.execute(
                text("""
                WITH prod AS (
                    SELECT p.product_id, p.activo, p.codigo_barras, p.created_at,
                           p.costo, p.precio_base
                    FROM productos p
                ), ventas_prod AS (
                    SELECT vd.product_id,
                           SUM(vd.sales_value * vd.cantidad - vd.retail_disc) AS ingreso,
                           SUM(vd.cantidad * COALESCE(pr.costo, 0)) AS costo_total
                    FROM venta_detalle vd
                    JOIN ventas v ON v.venta_id = vd.venta_id AND v.estado = 'confirmada'
                    JOIN productos pr ON pr.product_id = vd.product_id
                    GROUP BY vd.product_id
                )
                SELECT
                    (SELECT count(*) FROM prod WHERE activo) AS total_activos,
                    -- "nuevo" = alta reciente por la UI; se excluye el día de la
                    -- carga masiva del dataset para no inflar el KPI.
                    (SELECT count(*) FROM prod p2
                       WHERE p2.created_at >= CURRENT_DATE - INTERVAL '30 days'
                         AND p2.created_at::date <> (
                             SELECT mode() WITHIN GROUP (ORDER BY created_at::date)
                             FROM productos)) AS nuevos_30d,
                    (SELECT count(*) FROM prod WHERE codigo_barras IS NOT NULL) AS con_ean,
                    (SELECT count(*) FROM prod) AS total,
                    (SELECT count(*) FROM margenes_objetivo
                       WHERE factor_sensibilidad IS NOT NULL) AS cats_con_elasticidad,
                    (SELECT count(DISTINCT p.product_id) FROM productos p
                       JOIN margenes_objetivo mo ON mo.product_category = p.product_category
                       WHERE mo.factor_sensibilidad IS NOT NULL AND p.activo) AS skus_con_elasticidad,
                    (SELECT count(DISTINCT product_id) FROM promociones) AS promos_vigentes,
                    (SELECT count(*) FROM productos p
                       JOIN margenes_objetivo mo ON mo.product_category = p.product_category
                       WHERE p.activo AND p.precio_base > 0 AND p.costo IS NOT NULL
                         AND (p.precio_base - p.costo) / p.precio_base * 100
                             < mo.margen_objetivo_pct - 5) AS skus_bajo_margen,
                    COALESCE(
                        (SELECT SUM(ingreso - costo_total) / NULLIF(SUM(ingreso), 0) * 100
                         FROM ventas_prod), 0) AS margen_bruto_ponderado_pct
                """)
            )
        ).mappings().first()
        return dict(row) if row else {}

    async def unidades_mensuales(self, product_id: int) -> float:
        """Unidades/mes del producto sobre todo el histórico cargado (dataset ≈ 1
        año); base del simulador de impacto. 0 si nunca se vendió."""
        row = (
            await self.session.execute(
                text("""
                SELECT COALESCE(SUM(vd.cantidad), 0)::float AS uni,
                       GREATEST(
                         1,
                         EXTRACT(EPOCH FROM (MAX(v.fecha_hora) - MIN(v.fecha_hora)))
                           / (60*60*24*30.44)
                       ) AS meses
                FROM venta_detalle vd
                JOIN ventas v ON v.venta_id = vd.venta_id AND v.estado = 'confirmada'
                WHERE vd.product_id = :p
                """),
                {"p": product_id},
            )
        ).mappings().first()
        if not row or not row["uni"]:
            return 0.0
        return round(row["uni"] / float(row["meses"]), 1)

    async def factor_sensibilidad_categoria(self, categoria: str | None) -> float | None:
        if not categoria:
            return None
        return await self.session.scalar(
            text(
                "SELECT factor_sensibilidad FROM margenes_objetivo "
                "WHERE product_category = :c"
            ),
            {"c": categoria},
        )
