"""ClientesRepository — acceso a datos del módulo Clientes/Fidelización (feature 002).

El **gating de consentimiento** (FR-001) vive aquí y en el service, nunca en el
frontend: `household_ids_elegibles` filtra `activo = true AND consentimiento_datos
= true`, y los jobs de CLV/churn/campañas parten de esa lista.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Select, exists, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.campana import Campana
from src.models.churn_score import ChurnScore
from src.models.cliente import Cliente
from src.models.cliente_clv import ClienteClv
from src.models.cliente_demografico import ClienteDemografico
from src.models.cupon import Cupon
from src.models.cupon_enviado import CuponEnviado
from src.models.cupon_redimido import CuponRedimido
from src.models.evento_cliente import EventoCliente
from src.models.nivel_fidelizacion import NivelFidelizacion
from src.models.producto import Producto
from src.models.venta import Venta
from src.models.venta_detalle import VentaDetalle
from src.shared.cupon_hito import ProductoAncla
from src.shared.repository import BaseRepository


class ClientesRepository(BaseRepository[Cliente]):
    model = Cliente

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    def agregar(self, entity) -> None:
        self.session.add(entity)

    async def flush(self) -> None:
        await self.session.flush()

    async def refrescar(self, entity) -> None:
        await self.session.refresh(entity)

    # --- perfil ---
    async def get_cliente(self, household_id: int) -> Cliente | None:
        return await self.session.get(Cliente, household_id)

    async def existe_email(self, email: str, excepto: int | None = None) -> bool:
        stmt = select(Cliente.household_id).where(func.lower(Cliente.email) == email.lower())
        if excepto is not None:
            stmt = stmt.where(Cliente.household_id != excepto)
        return (await self.session.scalars(stmt)).first() is not None

    async def existe_documento(self, documento: str, excepto: int | None = None) -> bool:
        stmt = select(Cliente.household_id).where(Cliente.documento_identidad == documento)
        if excepto is not None:
            stmt = stmt.where(Cliente.household_id != excepto)
        return (await self.session.scalars(stmt)).first() is not None

    async def get_demografico(self, household_id: int) -> ClienteDemografico | None:
        return await self.session.get(ClienteDemografico, household_id)

    def clientes_query(
        self,
        *,
        search: str | None = None,
        activo: bool | None = None,
        nivel_fidelizacion_id: int | None = None,
    ) -> Select:
        stmt = select(Cliente)
        if search:
            patron = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Cliente.nombre.ilike(patron),
                    Cliente.email.ilike(patron),
                    Cliente.documento_identidad.ilike(patron),
                )
            )
        if activo is not None:
            stmt = stmt.where(Cliente.activo.is_(activo))
        if nivel_fidelizacion_id is not None:
            # Clientes cuyo CLV más reciente los deja en ese nivel.
            sub = (
                select(ClienteClv.nivel_id)
                .where(ClienteClv.household_id == Cliente.household_id)
                .order_by(ClienteClv.fecha_calculo.desc())
                .limit(1)
                .scalar_subquery()
            )
            stmt = stmt.where(sub == nivel_fidelizacion_id)
        return stmt

    # --- último CLV / churn (para enriquecer la respuesta) ---
    async def ultimo_clv(self, household_id: int) -> ClienteClv | None:
        stmt = (
            select(ClienteClv)
            .where(ClienteClv.household_id == household_id)
            .order_by(ClienteClv.fecha_calculo.desc())
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def nivel_previo(self, household_id: int, antes_de: date) -> int | None:
        """Nivel del CLV más reciente calculado ANTES de `antes_de` — para detectar
        el ascenso de nivel en la corrida actual del job (feature 002, FR-008)."""
        row = (
            await self.session.execute(
                text(
                    "SELECT nivel_id FROM cliente_clv "
                    "WHERE household_id = :h AND fecha_calculo < :f "
                    "ORDER BY fecha_calculo DESC LIMIT 1"
                ),
                {"h": household_id, "f": antes_de},
            )
        ).first()
        return row.nivel_id if row else None

    async def cupones_activos(self, household_id: int) -> list[dict]:
        """Cupones vigentes y no redimidos del cliente (mismo criterio que la
        ficha 360°) — se listan en el correo de ascenso de nivel."""
        rows = (
            await self.session.execute(
                text("""
                SELECT DISTINCT ON (cu.coupon_upc)
                       cu.coupon_upc, p.nombre AS producto, p.product_category AS categoria
                FROM campana_cliente cc
                JOIN cupones cu ON cu.campaign_id = cc.campaign_id
                JOIN campanas ca ON ca.campaign_id = cc.campaign_id
                JOIN productos p ON p.product_id = cu.product_id
                WHERE cc.household_id = :h
                  AND NOT EXISTS (SELECT 1 FROM cupon_redimido r
                                  WHERE r.household_id = cc.household_id
                                    AND r.coupon_upc = cu.coupon_upc)
                ORDER BY cu.coupon_upc
                LIMIT 8
                """),
                {"h": household_id},
            )
        ).mappings().all()
        return [dict(r) for r in rows]

    async def ultimo_churn(self, household_id: int) -> ChurnScore | None:
        stmt = (
            select(ChurnScore)
            .where(ChurnScore.household_id == household_id)
            .order_by(ChurnScore.fecha_calculo.desc())
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    # --- gating de consentimiento (FR-001) ---
    async def household_ids_elegibles(self) -> list[int]:
        stmt = select(Cliente.household_id).where(
            Cliente.activo.is_(True), Cliente.consentimiento_datos.is_(True)
        )
        return list((await self.session.scalars(stmt)).all())

    async def es_elegible(self, household_id: int) -> bool:
        stmt = select(
            exists().where(
                Cliente.household_id == household_id,
                Cliente.activo.is_(True),
                Cliente.consentimiento_datos.is_(True),
            )
        )
        return bool(await self.session.scalar(stmt))

    # ================================================= US2: CLV / niveles
    async def compras_y_margen_en_ventana(self, desde: datetime) -> dict[int, tuple[int, Decimal]]:
        """Por `household_id`: (nº de ventas confirmadas, Σ margen real) en la
        ventana. Margen = Σ (sales_value - productos.costo) · cantidad por línea.
        Sólo clientes elegibles (activos + con consentimiento)."""
        margen_linea = (
            VentaDetalle.sales_value - func.coalesce(Producto.costo, 0)
        ) * VentaDetalle.cantidad
        stmt = (
            select(
                Venta.household_id,
                func.count(func.distinct(Venta.venta_id)).label("compras"),
                func.coalesce(func.sum(margen_linea), 0).label("margen"),
            )
            .select_from(Venta)
            .join(VentaDetalle, VentaDetalle.venta_id == Venta.venta_id)
            .join(Producto, Producto.product_id == VentaDetalle.product_id)
            .join(Cliente, Cliente.household_id == Venta.household_id)
            .where(
                Venta.estado == "confirmada",
                Venta.household_id.is_not(None),
                Venta.fecha_hora >= desde,
                Cliente.activo.is_(True),
                Cliente.consentimiento_datos.is_(True),
            )
            .group_by(Venta.household_id)
        )
        return {
            row.household_id: (int(row.compras), Decimal(str(row.margen)))
            for row in (await self.session.execute(stmt)).all()
        }

    async def upsert_clv(
        self, household_id: int, score: Decimal, nivel_id: int | None, fecha: date
    ) -> None:
        stmt = pg_insert(ClienteClv).values(
            household_id=household_id,
            clv_score=score,
            nivel_id=nivel_id,
            fecha_calculo=fecha,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["household_id", "fecha_calculo"],
            set_={"clv_score": stmt.excluded.clv_score, "nivel_id": stmt.excluded.nivel_id},
        )
        await self.session.execute(stmt)

    # --- niveles de fidelización ---
    async def niveles(self) -> list[NivelFidelizacion]:
        stmt = select(NivelFidelizacion).order_by(NivelFidelizacion.umbral_clv_min)
        return list((await self.session.scalars(stmt)).all())

    async def get_nivel(self, nivel_id: int) -> NivelFidelizacion | None:
        return await self.session.get(NivelFidelizacion, nivel_id)

    # ================================================= US3: churn / riesgo de fuga
    async def fechas_compra_por_cliente(self) -> dict[int, list[date]]:
        """Fechas (día) de las ventas confirmadas de cada cliente elegible.
        El cálculo del ciclo (research §2) toma las últimas 10 en la capa de
        servicio; aquí se traen todas ordenadas."""
        stmt = (
            select(Venta.household_id, func.cast(Venta.fecha_hora, Date).label("dia"))
            .join(Cliente, Cliente.household_id == Venta.household_id)
            .where(
                Venta.estado == "confirmada",
                Venta.household_id.is_not(None),
                Cliente.activo.is_(True),
                Cliente.consentimiento_datos.is_(True),
            )
            .order_by(Venta.household_id, "dia")
        )
        salida: dict[int, list[date]] = {}
        for hid, dia in (await self.session.execute(stmt)).all():
            salida.setdefault(hid, []).append(dia)
        return salida

    async def upsert_churn(
        self,
        household_id: int,
        score: Decimal,
        ciclo_dias: int | None,
        severidad: str | None,
        fecha: date,
    ) -> None:
        stmt = pg_insert(ChurnScore).values(
            household_id=household_id,
            score=score,
            ciclo_compra_dias=ciclo_dias,
            severidad=severidad,
            fecha_calculo=fecha,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["household_id", "fecha_calculo"],
            set_={
                "score": stmt.excluded.score,
                "ciclo_compra_dias": stmt.excluded.ciclo_compra_dias,
                "severidad": stmt.excluded.severidad,
            },
        )
        await self.session.execute(stmt)

    def riesgo_fuga_query(self, *, severidad: str | None = None) -> Select:
        """Clientes con un `churn_score` reciente que tiene severidad. Se toma la
        fila más reciente por cliente vía subconsulta de fecha máxima."""
        fecha_max = (
            select(
                ChurnScore.household_id,
                func.max(ChurnScore.fecha_calculo).label("fmax"),
            )
            .group_by(ChurnScore.household_id)
            .subquery()
        )
        stmt = (
            select(ChurnScore, Cliente.nombre, Cliente.documento_identidad)
            .join(
                fecha_max,
                (ChurnScore.household_id == fecha_max.c.household_id)
                & (ChurnScore.fecha_calculo == fecha_max.c.fmax),
            )
            .join(Cliente, Cliente.household_id == ChurnScore.household_id)
            .where(ChurnScore.severidad.is_not(None))
        )
        if severidad is not None:
            stmt = stmt.where(ChurnScore.severidad == severidad)
        return stmt.order_by(ChurnScore.score.desc())

    async def riesgo_fuga_pagina(
        self, *, severidad: str | None, offset: int, limit: int
    ) -> tuple[int, list]:
        """`(total, [(ChurnScore, nombre, documento_identidad), ...])` — la query
        es multi-columna, así que no pasa por `BaseRepository.paginate` (scalars)."""
        stmt = self.riesgo_fuga_query(severidad=severidad)
        total = await self.session.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        filas = (await self.session.execute(stmt.offset(offset).limit(limit))).all()
        return int(total or 0), [tuple(f) for f in filas]

    async def dias_desde_ultima_compra(self, household_id: int, hasta: date) -> int | None:
        ultima = await self.session.scalar(
            select(func.max(func.cast(Venta.fecha_hora, Date))).where(
                Venta.household_id == household_id,
                Venta.estado == "confirmada",
            )
        )
        return (hasta - ultima).days if ultima else None

    # ================================================= US4: campañas por hito
    async def clientes_con_hito(self, hoy: date) -> list[tuple[Cliente, str]]:
        """Clientes elegibles (activos + con consentimiento) cuya `fecha_nacimiento`
        (→ `cumpleanos`) o `fecha_registro` (→ `aniversario_registro`) cae hoy."""
        mes, dia = hoy.month, hoy.day
        elegible = Cliente.activo.is_(True) & Cliente.consentimiento_datos.is_(True)
        salida: list[tuple[Cliente, str]] = []
        for tipo, col in (
            ("cumpleanos", Cliente.fecha_nacimiento),
            ("aniversario_registro", Cliente.fecha_registro),
        ):
            stmt = select(Cliente).where(
                elegible,
                col.is_not(None),
                func.extract("month", col) == mes,
                func.extract("day", col) == dia,
            )
            for cliente in (await self.session.scalars(stmt)).all():
                salida.append((cliente, tipo))
        return salida

    async def evento_existe(self, household_id: int, tipo_evento: str, fecha: date) -> bool:
        stmt = select(
            exists().where(
                EventoCliente.household_id == household_id,
                EventoCliente.tipo_evento == tipo_evento,
                EventoCliente.fecha == fecha,
            )
        )
        return bool(await self.session.scalar(stmt))

    async def crear_evento(self, household_id: int, tipo_evento: str, fecha: date) -> EventoCliente:
        evento = EventoCliente(household_id=household_id, tipo_evento=tipo_evento, fecha=fecha)
        self.session.add(evento)
        await self.session.flush()
        return evento

    async def productos_ancla(self) -> list[ProductoAncla]:
        stmt = select(
            Producto.product_id,
            Producto.es_ancla,
            Producto.activo,
            Producto.precio_base,
            Producto.costo,
        ).where(Producto.es_ancla.is_(True), Producto.activo.is_(True))
        return [
            ProductoAncla(pid, es_ancla, activo, precio, costo)
            for pid, es_ancla, activo, precio, costo in (await self.session.execute(stmt)).all()
        ]

    async def campana_hito(self, hoy: date) -> int:
        """Campaña permanente `categoria_sira = 'hito'` (una sola, get-or-create).
        Todos los cupones de cumpleaños/aniversario cuelgan de ella."""
        existente = await self.session.scalar(
            select(Campana.campaign_id).where(Campana.categoria_sira == "hito").limit(1)
        )
        if existente is not None:
            return existente
        campana = Campana(
            categoria_sira="hito",
            campaign_type=None,
            start_date=hoy,
            end_date=date(hoy.year + 50, 12, 31),
        )
        self.session.add(campana)
        await self.session.flush()
        return campana.campaign_id

    async def registrar_cupon(self, coupon_upc: str, product_id: int, campaign_id: int) -> None:
        stmt = pg_insert(Cupon).values(
            coupon_upc=coupon_upc, product_id=product_id, campaign_id=campaign_id
        )
        await self.session.execute(stmt.on_conflict_do_nothing())

    async def registrar_cupon_enviado(
        self,
        *,
        evento_id: int,
        household_id: int,
        coupon_upc: str,
        campaign_id: int,
        entregado: bool,
    ) -> CuponEnviado:
        envio = CuponEnviado(
            evento_id=evento_id,
            household_id=household_id,
            coupon_upc=coupon_upc,
            campaign_id=campaign_id,
            entregado=entregado,
        )
        self.session.add(envio)
        await self.session.flush()
        return envio

    async def registrar_redencion(
        self, *, household_id: int, coupon_upc: str, campaign_id: int, fecha: date
    ) -> CuponRedimido:
        red = CuponRedimido(
            household_id=household_id,
            coupon_upc=coupon_upc,
            campaign_id=campaign_id,
            redemption_date=fecha,
        )
        self.session.add(red)
        await self.session.flush()
        return red

    async def cupon_enviado_de(self, coupon_upc: str, household_id: int) -> CuponEnviado | None:
        stmt = (
            select(CuponEnviado)
            .where(CuponEnviado.coupon_upc == coupon_upc, CuponEnviado.household_id == household_id)
            .order_by(CuponEnviado.fecha_envio.desc())
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def tasa_redencion_por_hito(
        self, tipo_evento: str | None = None
    ) -> list[tuple[str, int, int]]:
        """`(tipo_evento, enviados, redimidos)` — redimido = existe `cupon_redimido`
        con el mismo `coupon_upc` y `household_id` que el envío (FR-014)."""
        redimido = (
            select(CuponRedimido.redemption_id)
            .where(
                CuponRedimido.coupon_upc == CuponEnviado.coupon_upc,
                CuponRedimido.household_id == CuponEnviado.household_id,
            )
            .exists()
        )
        stmt = (
            select(
                EventoCliente.tipo_evento,
                func.count(CuponEnviado.envio_id).label("enviados"),
                func.count().filter(redimido).label("redimidos"),
            )
            .select_from(CuponEnviado)
            .join(EventoCliente, EventoCliente.evento_id == CuponEnviado.evento_id)
            .group_by(EventoCliente.tipo_evento)
        )
        if tipo_evento is not None:
            stmt = stmt.where(EventoCliente.tipo_evento == tipo_evento)
        return [(t, int(e), int(r)) for t, e, r in (await self.session.execute(stmt)).all()]

    async def eventos_de_cliente(
        self, household_id: int
    ) -> list[tuple[EventoCliente, str | None, bool | None, bool]]:
        """`(evento, coupon_upc, entregado, redimido)` por cada hito del cliente."""
        redimido = (
            select(CuponRedimido.redemption_id)
            .where(
                CuponRedimido.coupon_upc == CuponEnviado.coupon_upc,
                CuponRedimido.household_id == CuponEnviado.household_id,
            )
            .exists()
        )
        stmt = (
            select(
                EventoCliente,
                CuponEnviado.coupon_upc,
                CuponEnviado.entregado,
                redimido.label("redimido"),
            )
            .outerjoin(CuponEnviado, CuponEnviado.evento_id == EventoCliente.evento_id)
            .where(EventoCliente.household_id == household_id)
            .order_by(EventoCliente.fecha.desc())
        )
        return [tuple(row) for row in (await self.session.execute(stmt)).all()]
