"""PromocionesRepository (feature 005) — acceso a datos de reglas de afinidad,
cupones de afinidad, clasificación ABC, candidatos a liquidación y colocación
promocional. Sin lógica de negocio (Principio XI). Consulta de solo lectura
contra `propuesta_ajuste_precio` de 003 para la exclusión de candidatos (FR-013).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cambio_clasificacion_abc import CambioClasificacionAbc
from src.models.campana import Campana
from src.models.candidato_liquidacion import CandidatoLiquidacion
from src.models.configuracion_promociones import ConfiguracionPromociones
from src.models.cupon import Cupon
from src.models.cupon_enviado import CuponEnviado
from src.models.cupon_redimido import CuponRedimido
from src.models.producto import Producto
from src.models.regla_afinidad import ReglaAfinidad
from src.shared.repository import BaseRepository


class PromocionesRepository(BaseRepository[ReglaAfinidad]):
    model = ReglaAfinidad

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    def agregar(self, entity) -> None:
        self.session.add(entity)

    async def flush(self) -> None:
        await self.session.flush()

    async def refrescar(self, entity) -> None:
        await self.session.refresh(entity)

    # ------------------------------------------------------------ configuración
    async def listar_configuracion(self) -> list[ConfiguracionPromociones]:
        stmt = select(ConfiguracionPromociones).order_by(ConfiguracionPromociones.clave)
        return list((await self.session.scalars(stmt)).all())

    async def get_config(self, clave: str) -> ConfiguracionPromociones | None:
        return await self.session.get(ConfiguracionPromociones, clave)

    async def valor_config(self, clave: str, default: Decimal) -> Decimal:
        fila = await self.get_config(clave)
        return Decimal(str(fila.valor)) if fila is not None else default

    # ------------------------------------------------- afinidad (US1)
    async def lineas_para_afinidad(self) -> list[dict]:
        rows = await self.session.execute(text("""
                SELECT vd.venta_id, vd.product_id
                FROM venta_detalle vd
                JOIN ventas v ON v.venta_id = vd.venta_id
                WHERE v.estado = 'confirmada'
            """))
        return [{"venta_id": r.venta_id, "product_id": r.product_id} for r in rows]

    async def reemplazar_reglas(self, nuevas: list[dict]) -> int:
        await self.session.execute(
            ReglaAfinidad.__table__.update()
            .where(ReglaAfinidad.estado == "vigente")
            .values(estado="reemplazada")
        )
        self.session.add_all(
            ReglaAfinidad(
                product_id_antecedente=r["antecedente"],
                product_id_consecuente=r["consecuente"],
                soporte=r["soporte"],
                confianza=r["confianza"],
                lift=r.get("lift"),
                estado="vigente",
            )
            for r in nuevas
        )
        await self.session.flush()
        return len(nuevas)

    def reglas_query(self, *, estado: str | None = None) -> Select:
        stmt = select(ReglaAfinidad)
        if estado is not None:
            stmt = stmt.where(ReglaAfinidad.estado == estado)
        return stmt

    async def get_regla(self, regla_id: int) -> ReglaAfinidad | None:
        return await self.session.get(ReglaAfinidad, regla_id)

    async def reglas_vigentes(self) -> list[dict]:
        stmt = select(
            ReglaAfinidad.regla_id,
            ReglaAfinidad.product_id_antecedente,
            ReglaAfinidad.product_id_consecuente,
            ReglaAfinidad.soporte,
            ReglaAfinidad.confianza,
        ).where(ReglaAfinidad.estado == "vigente")
        return [
            {
                "regla_id": rid,
                "antecedente": ant,
                "consecuente": con,
                "soporte": float(sop),
                "confianza": float(conf),
            }
            for rid, ant, con, sop, conf in (await self.session.execute(stmt)).all()
        ]

    async def productos_activos_ids(self) -> set[int]:
        stmt = select(Producto.product_id).where(Producto.activo.is_(True))
        return set((await self.session.scalars(stmt)).all())

    # ------------------------------------------------- cupón de afinidad (US2)
    async def venta_para_afinidad(self, venta_id: int) -> dict | None:
        row = (
            await self.session.execute(
                text("SELECT household_id, estado FROM ventas WHERE venta_id = :v"),
                {"v": venta_id},
            )
        ).first()
        if row is None:
            return None
        prods = await self.session.execute(
            text("SELECT DISTINCT product_id FROM venta_detalle WHERE venta_id = :v"),
            {"v": venta_id},
        )
        return {
            "household_id": row.household_id,
            "estado": row.estado,
            "product_ids": {r.product_id for r in prods},
        }

    async def cliente_con_consentimiento(self, household_id: int) -> bool:
        row = (
            await self.session.execute(
                text("SELECT activo, consentimiento_datos FROM clientes WHERE household_id = :h"),
                {"h": household_id},
            )
        ).first()
        return bool(row and row.activo and row.consentimiento_datos)

    async def cupon_afinidad_vigente(
        self, household_id: int, regla_id: int, desde: datetime
    ) -> bool:
        stmt = select(CuponEnviado.envio_id).where(
            CuponEnviado.household_id == household_id,
            CuponEnviado.regla_afinidad_id == regla_id,
            CuponEnviado.fecha_envio >= desde,
        )
        return (await self.session.scalars(stmt)).first() is not None

    async def campana_afinidad(self, hoy: date) -> int:
        existente = await self.session.scalar(
            select(Campana.campaign_id).where(Campana.categoria_sira == "afinidad").limit(1)
        )
        if existente is not None:
            return existente
        campana = Campana(
            categoria_sira="afinidad",
            campaign_type=None,
            start_date=hoy,
            end_date=date(hoy.year + 50, 12, 31),
        )
        self.session.add(campana)
        await self.session.flush()
        return campana.campaign_id

    async def registrar_cupon(self, coupon_upc: str, product_id: int, campaign_id: int) -> None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(Cupon).values(
            coupon_upc=coupon_upc, product_id=product_id, campaign_id=campaign_id
        )
        await self.session.execute(stmt.on_conflict_do_nothing())

    async def registrar_cupon_afinidad(
        self,
        *,
        household_id: int,
        coupon_upc: str,
        campaign_id: int,
        regla_id: int,
        entregado: bool,
    ) -> CuponEnviado:
        envio = CuponEnviado(
            evento_id=None,
            household_id=household_id,
            coupon_upc=coupon_upc,
            campaign_id=campaign_id,
            regla_afinidad_id=regla_id,
            entregado=entregado,
        )
        self.session.add(envio)
        await self.session.flush()
        return envio

    def cupones_afinidad_query(self, *, household_id: int | None = None) -> Select:
        stmt = (
            select(CuponEnviado, Cupon.product_id)
            .outerjoin(
                Cupon,
                (Cupon.coupon_upc == CuponEnviado.coupon_upc)
                & (Cupon.campaign_id == CuponEnviado.campaign_id),
            )
            .where(CuponEnviado.regla_afinidad_id.is_not(None))
        )
        if household_id is not None:
            stmt = stmt.where(CuponEnviado.household_id == household_id)
        return stmt.order_by(CuponEnviado.fecha_envio.desc())

    async def redimido(self, coupon_upc: str, household_id: int) -> bool:
        stmt = select(CuponRedimido.redemption_id).where(
            CuponRedimido.coupon_upc == coupon_upc,
            CuponRedimido.household_id == household_id,
        )
        return (await self.session.scalars(stmt)).first() is not None

    async def tasa_redencion_afinidad(self) -> tuple[int, int]:
        redimido = (
            select(CuponRedimido.redemption_id)
            .where(
                CuponRedimido.coupon_upc == CuponEnviado.coupon_upc,
                CuponRedimido.household_id == CuponEnviado.household_id,
            )
            .exists()
        )
        row = (
            await self.session.execute(
                select(
                    func.count(CuponEnviado.envio_id),
                    func.count().filter(redimido),
                ).where(CuponEnviado.regla_afinidad_id.is_not(None))
            )
        ).first()
        return int(row[0] or 0), int(row[1] or 0)

    # ------------------------------------------------- clasificación ABC (US3)
    async def valor_venta_por_categoria(self, desde: date) -> dict[str, dict[int, float]]:
        rows = await self.session.execute(
            text("""
                SELECT p.product_category AS categoria, vd.product_id,
                       COALESCE(SUM(vd.sales_value * vd.cantidad - vd.retail_disc), 0)::float
                           AS valor
                FROM productos p
                LEFT JOIN venta_detalle vd ON vd.product_id = p.product_id
                LEFT JOIN ventas v ON v.venta_id = vd.venta_id
                    AND v.estado = 'confirmada' AND v.fecha_hora >= :desde
                WHERE p.activo = true
                GROUP BY p.product_category, vd.product_id
            """),
            {"desde": desde},
        )
        salida: dict[str, dict[int, float]] = {}
        for r in rows:
            if r.product_id is None:
                continue
            salida.setdefault(r.categoria or "(sin categoría)", {})[r.product_id] = float(
                r.valor or 0
            )
        # productos sin ninguna venta en la ventana igual deben clasificarse
        prods = await self.session.execute(
            text("SELECT product_id, product_category FROM productos WHERE activo = true")
        )
        for r in prods:
            cat = r.product_category or "(sin categoría)"
            salida.setdefault(cat, {}).setdefault(r.product_id, 0.0)
        return salida

    async def clasificacion_actual(self) -> dict[int, str | None]:
        rows = await self.session.execute(
            text("SELECT product_id, clasificacion_abc FROM productos WHERE activo = true")
        )
        return {r.product_id: r.clasificacion_abc for r in rows}

    async def aplicar_clasificacion(self, cambios: list[dict], fecha: datetime) -> None:
        for c in cambios:
            await self.session.execute(
                text("UPDATE productos SET clasificacion_abc = :n WHERE product_id = :p"),
                {"n": c["nueva"], "p": c["product_id"]},
            )
            self.session.add(
                CambioClasificacionAbc(
                    product_id=c["product_id"],
                    clasificacion_anterior=c["anterior"],
                    clasificacion_nueva=c["nueva"],
                    fecha_calculo=fecha,
                )
            )
        await self.session.flush()

    async def cambios_abc(self, desde: datetime) -> list[CambioClasificacionAbc]:
        stmt = (
            select(CambioClasificacionAbc)
            .where(CambioClasificacionAbc.fecha_calculo >= desde)
            .order_by(
                CambioClasificacionAbc.fecha_calculo.desc(), CambioClasificacionAbc.product_id
            )
        )
        return list((await self.session.scalars(stmt)).all())

    async def ultima_fecha_clasificacion(self) -> datetime | None:
        return await self.session.scalar(select(func.max(CambioClasificacionAbc.fecha_calculo)))

    # ------------------------------------------------- liquidación (US3)
    async def product_ids_categoria_c(self) -> list[int]:
        rows = await self.session.execute(
            text("SELECT product_id FROM productos WHERE activo = true AND clasificacion_abc = 'C'")
        )
        return [r.product_id for r in rows]

    async def product_ids_con_precio_pendiente(self) -> set[int]:
        rows = await self.session.execute(
            text(
                "SELECT DISTINCT product_id FROM propuesta_ajuste_precio WHERE estado = 'pendiente'"
            )
        )
        return {r.product_id for r in rows}

    async def rotacion_local(
        self, product_ids: list[int], desde: date
    ) -> dict[tuple[int, int], float]:
        """`{(product_id, tienda_id): unidades vendidas desde `desde`}` para los
        productos dados, sobre los pares que existen en `inventario`."""
        if not product_ids:
            return {}
        rows = await self.session.execute(
            text("""
                SELECT i.product_id, i.tienda_id,
                       COALESCE((
                           SELECT SUM(vd.cantidad)
                           FROM venta_detalle vd
                           JOIN ventas v ON v.venta_id = vd.venta_id
                           WHERE vd.product_id = i.product_id AND v.tienda_id = i.tienda_id
                             AND v.estado = 'confirmada' AND v.fecha_hora >= :desde
                       ), 0)::float AS unidades
                FROM inventario i
                WHERE i.product_id = ANY(:pids)
            """),
            {"desde": desde, "pids": product_ids},
        )
        return {(r.product_id, r.tienda_id): float(r.unidades) for r in rows}

    async def upsert_candidato(self, fila: dict) -> None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(CandidatoLiquidacion).values(**fila)
        stmt = stmt.on_conflict_do_update(
            index_elements=["product_id", "tienda_id", "semana", "anio"],
            set_={
                "rotacion_reciente_calculada": stmt.excluded.rotacion_reciente_calculada,
                "descuento_sugerido_pct": stmt.excluded.descuento_sugerido_pct,
            },
        )
        await self.session.execute(stmt)

    def candidatos_query(self, *, tienda_id: int, semana: int, anio: int) -> Select:
        return select(CandidatoLiquidacion).where(
            CandidatoLiquidacion.tienda_id == tienda_id,
            CandidatoLiquidacion.semana == semana,
            CandidatoLiquidacion.anio == anio,
        )

    async def get_candidato(self, candidato_id: int) -> CandidatoLiquidacion | None:
        return await self.session.get(CandidatoLiquidacion, candidato_id)

    # ------------------------------------------------- colocación (US4)
    async def crear_colocacion(self, fila: dict) -> int:
        row = await self.session.execute(
            text(
                "INSERT INTO promociones "
                "(product_id, tienda_id, display_location, mailer_location, semana, anio) "
                "VALUES (:product_id, :tienda_id, :display_location, :mailer_location, "
                ":semana, :anio) RETURNING promocion_id"
            ),
            fila,
        )
        return row.scalar_one()

    async def colocaciones(
        self, *, tienda_id: int | None, semana: int | None, anio: int | None
    ) -> list[dict]:
        cond = ["1=1"]
        params: dict = {}
        if tienda_id is not None:
            cond.append("tienda_id = :tienda_id")
            params["tienda_id"] = tienda_id
        if semana is not None:
            cond.append("semana = :semana")
            params["semana"] = semana
        if anio is not None:
            cond.append("anio = :anio")
            params["anio"] = anio
        where = " AND ".join(cond)
        rows = await self.session.execute(
            text(
                "SELECT promocion_id, product_id, tienda_id, display_location, mailer_location, "
                f"semana, anio FROM promociones WHERE {where} ORDER BY promocion_id DESC"
            ),
            params,
        )
        return [dict(r._mapping) for r in rows]

    async def get_colocacion(self, promocion_id: int) -> dict | None:
        row = (
            await self.session.execute(
                text(
                    "SELECT promocion_id, product_id, tienda_id, semana, anio "
                    "FROM promociones WHERE promocion_id = :id"
                ),
                {"id": promocion_id},
            )
        ).first()
        return dict(row._mapping) if row else None

    async def unidades_producto_semana(
        self, product_id: int, tienda_id: int | None, semana: int, anio: int
    ) -> int:
        cond = "v.semana = :semana AND EXTRACT(year FROM v.fecha_hora)::int = :anio"
        params: dict = {"p": product_id, "semana": semana, "anio": anio}
        if tienda_id is not None:
            cond += " AND v.tienda_id = :tienda_id"
            params["tienda_id"] = tienda_id
        row = await self.session.execute(
            text(f"""
                SELECT COALESCE(SUM(vd.cantidad), 0)::int AS u
                FROM venta_detalle vd
                JOIN ventas v ON v.venta_id = vd.venta_id
                WHERE vd.product_id = :p AND v.estado = 'confirmada' AND {cond}
            """),
            params,
        )
        return int(row.scalar_one() or 0)
