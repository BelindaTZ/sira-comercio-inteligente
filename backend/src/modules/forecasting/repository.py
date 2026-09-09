"""ForecastingRepository (feature 004) — acceso a datos del pronóstico de demanda.

Lee el historial de ventas y las variables exógenas de tablas ya existentes
(001/esquema base) y persiste la salida del modelo (versión, pronósticos,
monitoreo). Sin lógica de negocio (Principio XI).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.configuracion_pronostico import ConfiguracionPronostico
from src.models.modelo_demanda import ModeloDemanda
from src.models.monitoreo_precision_modelo import MonitoreoPrecisionModelo
from src.models.pronostico_demanda import PronosticoDemanda
from src.shared.repository import BaseRepository


class ForecastingRepository(BaseRepository[ModeloDemanda]):
    model = ModeloDemanda

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    def agregar(self, entity) -> None:
        self.session.add(entity)

    async def flush(self) -> None:
        await self.session.flush()

    async def refrescar(self, entity) -> None:
        await self.session.refresh(entity)

    # ------------------------------------------------------------ configuración
    async def listar_configuracion(self) -> list[ConfiguracionPronostico]:
        stmt = select(ConfiguracionPronostico).order_by(ConfiguracionPronostico.clave)
        return list((await self.session.scalars(stmt)).all())

    async def get_config(self, clave: str) -> ConfiguracionPronostico | None:
        return await self.session.get(ConfiguracionPronostico, clave)

    async def valor_config(self, clave: str, default: Decimal) -> Decimal:
        fila = await self.get_config(clave)
        return Decimal(str(fila.valor)) if fila is not None else default

    # ------------------------------------------------- historial + exógenas
    async def ventas_semanales(self) -> list[dict]:
        """Unidades vendidas por producto×tienda×semana (ventas confirmadas).
        `anio` se deriva de `ventas.fecha_hora` (la tabla `ventas` no lo almacena)."""
        rows = await self.session.execute(text("""
                SELECT vd.product_id, v.tienda_id, v.semana,
                       EXTRACT(year FROM v.fecha_hora)::int AS anio,
                       SUM(vd.cantidad)::float AS unidades
                FROM venta_detalle vd
                JOIN ventas v ON v.venta_id = vd.venta_id
                WHERE v.estado = 'confirmada'
                GROUP BY vd.product_id, v.tienda_id, v.semana,
                         EXTRACT(year FROM v.fecha_hora)
            """))
        return [dict(r._mapping) for r in rows]

    async def semanas_con_promocion(self) -> set[tuple[int, int, int]]:
        rows = await self.session.execute(
            text("SELECT DISTINCT product_id, semana, anio FROM promociones")
        )
        return {(r.product_id, r.semana, r.anio) for r in rows}

    async def cambios_precio(self) -> list[dict]:
        """Cambios de precio con su semana/año (de `fecha_inicio`) y la magnitud
        relativa respecto a la vigencia anterior del mismo producto."""
        rows = await self.session.execute(text("""
                SELECT product_id,
                       EXTRACT(week FROM fecha_inicio)::int  AS semana,
                       EXTRACT(year FROM fecha_inicio)::int  AS anio,
                       precio::float                        AS precio,
                       LAG(precio) OVER (PARTITION BY product_id
                                         ORDER BY fecha_inicio)::float AS precio_prev
                FROM historial_precios
                WHERE tienda_id IS NULL
            """))
        return [dict(r._mapping) for r in rows]

    async def quiebres_semanales(self) -> list[dict]:
        """Eventos de quiebre por producto/tienda/semana, con la categoría del producto."""
        rows = await self.session.execute(text("""
                SELECT e.product_id, e.tienda_id,
                       EXTRACT(week FROM e.fecha_hora)::int AS semana,
                       EXTRACT(year FROM e.fecha_hora)::int AS anio,
                       p.product_category AS categoria
                FROM eventos_quiebre_stock e
                JOIN productos p ON p.product_id = e.product_id
            """))
        return [dict(r._mapping) for r in rows]

    async def categoria_por_producto(self) -> dict[int, str | None]:
        rows = await self.session.execute(
            text("SELECT product_id, product_category FROM productos")
        )
        return {r.product_id: r.product_category for r in rows}

    # --------------------------------------------------- persistencia modelo
    async def crear_modelo(self, wape_validacion: float, productos_cubiertos: int) -> ModeloDemanda:
        modelo = ModeloDemanda(metrica_precision_validacion=wape_validacion, estado="pendiente")
        self.session.add(modelo)
        await self.session.flush()
        modelo.observaciones = f"{productos_cubiertos} combinaciones producto/tienda cubiertas"
        await self.session.flush()
        return modelo

    async def guardar_pronosticos(self, modelo_id: int, filas: list[dict]) -> None:
        self.session.add_all(
            PronosticoDemanda(
                modelo_id=modelo_id,
                product_id=f["product_id"],
                tienda_id=f["tienda_id"],
                semana=f["semana"],
                anio=f["anio"],
                cantidad_pronosticada=max(0.0, round(float(f["cantidad_pronosticada"]), 2)),
            )
            for f in filas
        )
        await self.session.flush()

    async def get_modelo(self, modelo_id: int) -> ModeloDemanda | None:
        return await self.session.get(ModeloDemanda, modelo_id)

    async def modelo_aprobado(self) -> ModeloDemanda | None:
        stmt = select(ModeloDemanda).where(ModeloDemanda.estado == "aprobado")
        return (await self.session.scalars(stmt)).first()

    def modelos_query(self, *, estado: str | None = None) -> Select:
        stmt = select(ModeloDemanda)
        if estado is not None:
            stmt = stmt.where(ModeloDemanda.estado == estado)
        return stmt

    async def contar_pronosticos(self, modelo_id: int) -> int:
        """Combinaciones producto/tienda distintas que el modelo cubre (no el
        total de filas: el modelo emite varias semanas de horizonte por par)."""
        pares = (
            select(PronosticoDemanda.product_id, PronosticoDemanda.tienda_id)
            .where(PronosticoDemanda.modelo_id == modelo_id)
            .distinct()
            .subquery()
        )
        return int(await self.session.scalar(select(func.count()).select_from(pares)) or 0)

    async def pronostico_vigente_proximo(
        self, product_id: int, tienda_id: int
    ) -> PronosticoDemanda | None:
        """El pronóstico más temprano (próxima semana) del modelo vigente para ese
        producto/tienda — lo consume el cálculo diario de reposición de 001."""
        stmt = (
            select(PronosticoDemanda)
            .join(ModeloDemanda, ModeloDemanda.modelo_id == PronosticoDemanda.modelo_id)
            .where(
                ModeloDemanda.estado == "aprobado",
                PronosticoDemanda.product_id == product_id,
                PronosticoDemanda.tienda_id == tienda_id,
            )
            .order_by(PronosticoDemanda.anio, PronosticoDemanda.semana)
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def pronostico_vigente(
        self, product_id: int, tienda_id: int, semana: int, anio: int
    ) -> PronosticoDemanda | None:
        stmt = (
            select(PronosticoDemanda)
            .join(ModeloDemanda, ModeloDemanda.modelo_id == PronosticoDemanda.modelo_id)
            .where(
                ModeloDemanda.estado == "aprobado",
                PronosticoDemanda.product_id == product_id,
                PronosticoDemanda.tienda_id == tienda_id,
                PronosticoDemanda.semana == semana,
                PronosticoDemanda.anio == anio,
            )
        )
        return (await self.session.scalars(stmt)).first()

    # --------------------------------------------------- monitoreo
    async def ventas_reales_de_semana(self, semana: int, anio: int) -> dict[tuple[int, int], float]:
        rows = await self.session.execute(
            text("""
                SELECT vd.product_id, v.tienda_id, SUM(vd.cantidad)::float AS unidades
                FROM venta_detalle vd
                JOIN ventas v ON v.venta_id = vd.venta_id
                WHERE v.estado = 'confirmada' AND v.semana = :semana
                  AND EXTRACT(year FROM v.fecha_hora)::int = :anio
                GROUP BY vd.product_id, v.tienda_id
            """),
            {"semana": semana, "anio": anio},
        )
        return {(r.product_id, r.tienda_id): r.unidades for r in rows}

    async def pronosticos_de_semana(
        self, modelo_id: int, semana: int, anio: int
    ) -> dict[tuple[int, int], float]:
        stmt = select(
            PronosticoDemanda.product_id,
            PronosticoDemanda.tienda_id,
            PronosticoDemanda.cantidad_pronosticada,
        ).where(
            PronosticoDemanda.modelo_id == modelo_id,
            PronosticoDemanda.semana == semana,
            PronosticoDemanda.anio == anio,
        )
        return {
            (pid, tid): float(cant) for pid, tid, cant in (await self.session.execute(stmt)).all()
        }

    async def guardar_monitoreo(
        self, modelo_id: int, semana: int, anio: int, metrica: float, supero: bool
    ) -> MonitoreoPrecisionModelo:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(MonitoreoPrecisionModelo).values(
            modelo_id=modelo_id,
            semana=semana,
            anio=anio,
            metrica_precision=metrica,
            supero_umbral_alerta=supero,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["modelo_id", "semana", "anio"],
            set_={
                "metrica_precision": stmt.excluded.metrica_precision,
                "supero_umbral_alerta": stmt.excluded.supero_umbral_alerta,
                "fecha_calculo": func.now(),
            },
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.session.scalar(
            select(MonitoreoPrecisionModelo).where(
                MonitoreoPrecisionModelo.modelo_id == modelo_id,
                MonitoreoPrecisionModelo.semana == semana,
                MonitoreoPrecisionModelo.anio == anio,
            )
        )

    async def monitoreo_de_modelo(self, modelo_id: int) -> list[MonitoreoPrecisionModelo]:
        stmt = (
            select(MonitoreoPrecisionModelo)
            .where(MonitoreoPrecisionModelo.modelo_id == modelo_id)
            .order_by(MonitoreoPrecisionModelo.anio, MonitoreoPrecisionModelo.semana)
        )
        return list((await self.session.scalars(stmt)).all())

    async def alertas_monitoreo(self) -> list[MonitoreoPrecisionModelo]:
        """La medición semanal más reciente por modelo, sólo si superó el umbral."""
        sub = (
            select(
                MonitoreoPrecisionModelo.modelo_id,
                func.max(
                    MonitoreoPrecisionModelo.anio * 53 + MonitoreoPrecisionModelo.semana
                ).label("t_max"),
            )
            .group_by(MonitoreoPrecisionModelo.modelo_id)
            .subquery()
        )
        stmt = (
            select(MonitoreoPrecisionModelo)
            .join(
                sub,
                (MonitoreoPrecisionModelo.modelo_id == sub.c.modelo_id)
                & (
                    MonitoreoPrecisionModelo.anio * 53 + MonitoreoPrecisionModelo.semana
                    == sub.c.t_max
                ),
            )
            .where(MonitoreoPrecisionModelo.supero_umbral_alerta.is_(True))
        )
        return list((await self.session.scalars(stmt)).all())

    # --------------------------------------------------- demanda perdida
    async def demanda_perdida(
        self, desde: date, hasta: date, tienda_id: int | None = None
    ) -> list[dict]:
        params: dict = {"desde": desde, "hasta": hasta}
        filtro_tienda = ""
        if tienda_id is not None:
            filtro_tienda = "AND e.tienda_id = :tienda_id"
            params["tienda_id"] = tienda_id
        rows = await self.session.execute(
            text(f"""
                SELECT e.tienda_id,
                       COALESCE(p.product_category, '(sin categoría)') AS product_category,
                       COUNT(*)::int AS cantidad_eventos,
                       COALESCE(SUM(e.demanda_estimada_no_satisfecha), 0)::int
                           AS demanda_estimada_no_satisfecha
                FROM eventos_quiebre_stock e
                JOIN productos p ON p.product_id = e.product_id
                WHERE e.fecha_hora >= :desde AND e.fecha_hora < :hasta {filtro_tienda}
                GROUP BY e.tienda_id, p.product_category
                ORDER BY e.tienda_id, product_category
            """),
            params,
        )
        return [dict(r._mapping) for r in rows]

    async def demanda_perdida_por_producto(
        self, desde: date, hasta: date, tienda_id: int | None = None
    ) -> list[dict]:
        """Igual que `demanda_perdida` pero por SKU — para que la pantalla ofrezca
        una acción concreta (solicitar reposición) sobre cada producto afectado."""
        params: dict = {"desde": desde, "hasta": hasta}
        filtro_tienda = ""
        if tienda_id is not None:
            filtro_tienda = "AND e.tienda_id = :tienda_id"
            params["tienda_id"] = tienda_id
        rows = await self.session.execute(
            text(f"""
                SELECT e.product_id,
                       p.nombre AS producto_nombre,
                       COALESCE(p.product_category, '(sin categoría)') AS product_category,
                       max(e.tienda_id) AS tienda_id,
                       count(*)::int AS cantidad_eventos,
                       COALESCE(sum(e.demanda_estimada_no_satisfecha), 0)::int
                           AS demanda_estimada_no_satisfecha,
                       bool_or(e.es_alta_demanda) AS alta_demanda,
                       max(e.fecha_hora) AS ultimo_evento
                FROM eventos_quiebre_stock e
                JOIN productos p ON p.product_id = e.product_id
                WHERE e.fecha_hora >= :desde AND e.fecha_hora < :hasta {filtro_tienda}
                GROUP BY e.product_id, p.nombre, p.product_category
                ORDER BY demanda_estimada_no_satisfecha DESC, cantidad_eventos DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in rows]
