"""PricingRepository (feature 003) — acceso a datos de márgenes, propuestas de
ajuste, revisión de margen bajo, competencia y configuración. Sin lógica de
negocio (Principio XI)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Select, and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.competidor import Competidor
from src.models.configuracion_pricing import ConfiguracionPricing
from src.models.historial_precio import HistorialPrecio
from src.models.margen_objetivo import MargenObjetivo
from src.models.precio_competencia import PrecioCompetencia
from src.models.producto import Producto
from src.models.propuesta_ajuste_precio import PropuestaAjustePrecio
from src.models.revision_margen_bajo import RevisionMargenBajo
from src.models.venta import Venta
from src.models.venta_detalle import VentaDetalle
from src.shared.repository import BaseRepository


class PricingRepository(BaseRepository[MargenObjetivo]):
    model = MargenObjetivo

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    def agregar(self, entity) -> None:
        self.session.add(entity)

    async def flush(self) -> None:
        await self.session.flush()

    async def refrescar(self, entity) -> None:
        await self.session.refresh(entity)

    # ---------------------------------------------------------------- productos
    async def get_producto(self, product_id: int) -> Producto | None:
        return await self.session.get(Producto, product_id)

    # product_id >= 90_000_000 → alta por la UI (research.md §5 / seed de 001):
    # esos productos llevan código de barras real y sí resuelven en Open Prices.
    _UMBRAL_PRODUCTO_EN_VIVO = 90_000_000

    async def productos_en_vivo_con_barcode(self) -> list[Producto]:
        stmt = select(Producto).where(
            Producto.product_id >= self._UMBRAL_PRODUCTO_EN_VIVO,
            Producto.codigo_barras.is_not(None),
            Producto.activo.is_(True),
        )
        return list((await self.session.scalars(stmt)).all())

    async def productos_de_categoria(self, product_category: str) -> list[Producto]:
        stmt = select(Producto).where(
            Producto.product_category == product_category, Producto.activo.is_(True)
        )
        return list((await self.session.scalars(stmt)).all())

    # ------------------------------------------------------- márgenes objetivo
    async def listar_margenes(self) -> list[MargenObjetivo]:
        stmt = select(MargenObjetivo).order_by(MargenObjetivo.product_category)
        return list((await self.session.scalars(stmt)).all())

    async def get_margen(self, product_category: str) -> MargenObjetivo | None:
        return await self.session.get(MargenObjetivo, product_category)

    async def margenes_con_regla(self) -> list[MargenObjetivo]:
        stmt = select(MargenObjetivo).where(MargenObjetivo.factor_sensibilidad.is_not(None))
        return list((await self.session.scalars(stmt)).all())

    # ------------------------------------------------------------ configuración
    async def listar_configuracion(self) -> list[ConfiguracionPricing]:
        stmt = select(ConfiguracionPricing).order_by(ConfiguracionPricing.clave)
        return list((await self.session.scalars(stmt)).all())

    async def get_config(self, clave: str) -> ConfiguracionPricing | None:
        return await self.session.get(ConfiguracionPricing, clave)

    async def valor_config(self, clave: str, default: Decimal) -> Decimal:
        fila = await self.get_config(clave)
        return Decimal(str(fila.valor)) if fila is not None else default

    # ------------------------------------------------------ propuestas ajuste
    def propuestas_query(
        self, *, estado: str | None = None, product_category: str | None = None
    ) -> Select:
        stmt = select(PropuestaAjustePrecio)
        if estado is not None:
            stmt = stmt.where(PropuestaAjustePrecio.estado == estado)
        if product_category is not None:
            sub = select(Producto.product_id).where(Producto.product_category == product_category)
            stmt = stmt.where(PropuestaAjustePrecio.product_id.in_(sub))
        return stmt

    async def get_propuesta(self, propuesta_id: int) -> PropuestaAjustePrecio | None:
        return await self.session.get(PropuestaAjustePrecio, propuesta_id)

    async def propuesta_pendiente_de(self, product_id: int) -> PropuestaAjustePrecio | None:
        stmt = select(PropuestaAjustePrecio).where(
            PropuestaAjustePrecio.product_id == product_id,
            PropuestaAjustePrecio.estado == "pendiente",
        )
        return (await self.session.scalars(stmt)).first()

    async def publicar_precio(self, product_id: int, nuevo_precio: Decimal, hoy: date) -> None:
        """Transacción de research.md §1: cierra la vigencia anterior en
        `historial_precios`, inserta la nueva y actualiza `productos.precio_base`."""
        await self.session.execute(
            HistorialPrecio.__table__.update()
            .where(
                HistorialPrecio.product_id == product_id,
                HistorialPrecio.tienda_id.is_(None),
                HistorialPrecio.fecha_fin.is_(None),
            )
            .values(fecha_fin=hoy)
        )
        self.session.add(
            HistorialPrecio(
                product_id=product_id, tienda_id=None, precio=nuevo_precio, fecha_inicio=hoy
            )
        )
        producto = await self.session.get(Producto, product_id)
        if producto is not None:
            producto.precio_base = nuevo_precio
        await self.session.flush()

    # -------------------------------------------------------- margen bajo (US3)
    def margen_bajo_query(
        self, *, tienda_id: int | None = None, revisado: bool | None = None
    ) -> Select:
        rev = select(
            RevisionMargenBajo.venta_detalle_id, RevisionMargenBajo.accion_correctiva
        ).subquery()
        stmt = (
            select(
                VentaDetalle,
                Venta.venta_id,
                Venta.tienda_id,
                Venta.fecha_hora,
                rev.c.accion_correctiva,
            )
            .join(Venta, Venta.venta_id == VentaDetalle.venta_id)
            .outerjoin(rev, rev.c.venta_detalle_id == VentaDetalle.venta_detalle_id)
            .where(VentaDetalle.margen_bajo_minimo.is_(True))
        )
        if tienda_id is not None:
            stmt = stmt.where(Venta.tienda_id == tienda_id)
        if revisado is True:
            stmt = stmt.where(rev.c.accion_correctiva.is_not(None))
        elif revisado is False:
            stmt = stmt.where(rev.c.accion_correctiva.is_(None))
        return stmt.order_by(Venta.fecha_hora.desc(), VentaDetalle.venta_detalle_id.desc())

    async def margen_bajo_pagina(
        self, *, tienda_id: int | None, revisado: bool | None, offset: int, limit: int
    ) -> tuple[int, list]:
        stmt = self.margen_bajo_query(tienda_id=tienda_id, revisado=revisado)
        total = await self.session.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        filas = (await self.session.execute(stmt.offset(offset).limit(limit))).all()
        return int(total or 0), [tuple(f) for f in filas]

    async def get_linea(self, venta_detalle_id: int) -> VentaDetalle | None:
        return await self.session.get(VentaDetalle, venta_detalle_id)

    async def upsert_revision(self, venta_detalle_id: int, revisado_por: int, accion: str) -> None:
        stmt = pg_insert(RevisionMargenBajo).values(
            venta_detalle_id=venta_detalle_id,
            revisado_por=revisado_por,
            accion_correctiva=accion,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["venta_detalle_id"],
            set_={
                "revisado_por": stmt.excluded.revisado_por,
                "accion_correctiva": stmt.excluded.accion_correctiva,
                "fecha_revision": func.now(),
            },
        )
        await self.session.execute(stmt)

    # --------------------------------------------------------- reporte margen
    async def agregado_margen_por_categoria(
        self, desde: date, hasta: date, product_category: str | None = None
    ) -> list[tuple[str, int, Decimal, Decimal]]:
        """`(categoria, unidades, ingreso_total, costo_total)` de las líneas de
        ventas confirmadas en el rango [desde, hasta]. `ingreso = sales_value *
        cantidad - retail_disc` (precio ya descontado); `costo = productos.costo *
        cantidad`."""
        ingreso = (
            VentaDetalle.sales_value * VentaDetalle.cantidad
            - VentaDetalle.retail_disc
            - VentaDetalle.coupon_disc
            - VentaDetalle.coupon_match_disc
        )
        costo = func.coalesce(Producto.costo, 0) * VentaDetalle.cantidad
        stmt = (
            select(
                Producto.product_category,
                func.sum(VentaDetalle.cantidad),
                func.sum(ingreso),
                func.sum(costo),
            )
            .select_from(VentaDetalle)
            .join(Venta, Venta.venta_id == VentaDetalle.venta_id)
            .join(Producto, Producto.product_id == VentaDetalle.product_id)
            .where(
                Venta.estado == "confirmada",
                func.date(Venta.fecha_hora) >= desde,
                func.date(Venta.fecha_hora) <= hasta,
            )
            .group_by(Producto.product_category)
            .order_by(Producto.product_category)
        )
        if product_category is not None:
            stmt = stmt.where(Producto.product_category == product_category)
        return [
            (cat or "(sin categoría)", int(u or 0), Decimal(str(i or 0)), Decimal(str(c or 0)))
            for cat, u, i, c in (await self.session.execute(stmt)).all()
        ]

    # ----------------------------------------------------------- competencia
    async def listar_competidores(
        self, *, tipo: str | None = None, ciudad: str | None = None
    ) -> list[Competidor]:
        stmt = select(Competidor).order_by(Competidor.nombre)
        if tipo is not None:
            stmt = stmt.where(Competidor.tipo == tipo)
        if ciudad is not None:
            stmt = stmt.where(Competidor.ciudad == ciudad)
        return list((await self.session.scalars(stmt)).all())

    async def get_competidor(self, competidor_id: int) -> Competidor | None:
        return await self.session.get(Competidor, competidor_id)

    async def agregar_precio_competencia(self, fila: PrecioCompetencia) -> PrecioCompetencia:
        self.session.add(fila)
        await self.session.flush()
        await self.session.refresh(fila)
        return fila

    async def precios_competencia_de(self, product_id: int) -> list[PrecioCompetencia]:
        stmt = (
            select(PrecioCompetencia)
            .where(PrecioCompetencia.product_id == product_id)
            .order_by(
                PrecioCompetencia.fecha_captura.desc(),
                PrecioCompetencia.precio_competencia_id.desc(),
            )
        )
        return list((await self.session.scalars(stmt)).all())

    async def precio_competencia_mas_reciente_por_producto(
        self,
    ) -> list[tuple[int, str | None, Decimal, Decimal, str, date]]:
        """`(product_id, categoria, precio_base, precio_competencia, fuente, fecha)`
        con la fila de `fecha_captura` más reciente por producto (sin importar la
        fuente). Sólo productos con `precio_base` y al menos una fila."""
        fecha_max = (
            select(
                PrecioCompetencia.product_id,
                func.max(PrecioCompetencia.fecha_captura).label("fmax"),
            )
            .group_by(PrecioCompetencia.product_id)
            .subquery()
        )
        # de las filas con la fecha máxima, la de mayor id (última capturada ese día)
        id_max = (
            select(
                PrecioCompetencia.product_id,
                func.max(PrecioCompetencia.precio_competencia_id).label("imax"),
            )
            .join(
                fecha_max,
                and_(
                    PrecioCompetencia.product_id == fecha_max.c.product_id,
                    PrecioCompetencia.fecha_captura == fecha_max.c.fmax,
                ),
            )
            .group_by(PrecioCompetencia.product_id)
            .subquery()
        )
        stmt = (
            select(
                Producto.product_id,
                Producto.product_category,
                Producto.precio_base,
                PrecioCompetencia.precio,
                PrecioCompetencia.fuente_captura,
                PrecioCompetencia.fecha_captura,
            )
            .join(id_max, id_max.c.imax == PrecioCompetencia.precio_competencia_id)
            .join(Producto, Producto.product_id == PrecioCompetencia.product_id)
            .where(Producto.precio_base.is_not(None))
            .order_by(Producto.product_id)
        )
        return [
            (
                pid,
                cat,
                Decimal(str(pb)),
                Decimal(str(pc)),
                fuente,
                fecha,
            )
            for pid, cat, pb, pc, fuente, fecha in (await self.session.execute(stmt)).all()
        ]
