"""CampanasRepository — acceso a datos de campañas de reactivación (US5, feature 002).

El grupo de control (FR-017) y la tasa de retorno por grupo (FR-018) se resuelven
aquí; la comparación de uplift la hace la columna generada de `campana_resultado`.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.campana import Campana
from src.models.campana_cliente import CampanaCliente
from src.models.campana_resultado import CampanaResultado
from src.models.cliente import Cliente
from src.models.cupon import Cupon
from src.models.cupon_enviado import CuponEnviado
from src.models.producto import Producto
from src.models.venta import Venta
from src.shared.cupon_hito import ProductoAncla
from src.shared.repository import BaseRepository


class CampanasRepository(BaseRepository[Campana]):
    model = Campana

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def flush(self) -> None:
        await self.session.flush()

    # --- creación ---
    async def crear_campana(
        self, *, start_date: date, end_date: date, categoria_sira: str, nombre: str | None = None
    ) -> Campana:
        campana = Campana(
            start_date=start_date,
            end_date=end_date,
            categoria_sira=categoria_sira,
            nombre=nombre,
        )
        self.session.add(campana)
        await self.session.flush()
        return campana

    async def agregar_miembros(self, campaign_id: int, miembros: list[tuple[int, str]]) -> None:
        self.session.add_all(
            CampanaCliente(campaign_id=campaign_id, household_id=hid, grupo=grupo)
            for hid, grupo in miembros
        )
        await self.session.flush()

    # --- lectura ---
    async def get_campana(self, campaign_id: int) -> Campana | None:
        return await self.session.get(Campana, campaign_id)

    async def miembros(self, campaign_id: int) -> list[CampanaCliente]:
        stmt = (
            select(CampanaCliente)
            .where(CampanaCliente.campaign_id == campaign_id)
            .order_by(CampanaCliente.household_id)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_resultado(self, campaign_id: int) -> CampanaResultado | None:
        return await self.session.get(CampanaResultado, campaign_id)

    def campanas_query(self, *, categoria_sira: str | None = None) -> Select:
        stmt = select(Campana)
        if categoria_sira is not None:
            stmt = stmt.where(Campana.categoria_sira == categoria_sira)
        return stmt

    async def household_ids_no_elegibles(self, household_ids: list[int]) -> list[int]:
        """De la lista dada, los que NO son `activo AND consentimiento_datos`
        (incluye los que no existen). Gating de FR-001 aplicado a la segmentación."""
        if not household_ids:
            return []
        elegibles = set(
            (
                await self.session.scalars(
                    select(Cliente.household_id).where(
                        Cliente.household_id.in_(household_ids),
                        Cliente.activo.is_(True),
                        Cliente.consentimiento_datos.is_(True),
                    )
                )
            ).all()
        )
        return [hid for hid in household_ids if hid not in elegibles]

    async def clientes_por_ids(self, household_ids: list[int]) -> dict[int, Cliente]:
        if not household_ids:
            return {}
        rows = await self.session.scalars(
            select(Cliente).where(Cliente.household_id.in_(household_ids))
        )
        return {c.household_id: c for c in rows}

    # --- envío ---
    async def campana_enviada(self, campaign_id: int) -> bool:
        stmt = select(func.count(CuponEnviado.envio_id)).where(
            CuponEnviado.campaign_id == campaign_id
        )
        return bool(await self.session.scalar(stmt))

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

    async def registrar_cupon(self, coupon_upc: str, product_id: int, campaign_id: int) -> None:
        stmt = pg_insert(Cupon).values(
            coupon_upc=coupon_upc, product_id=product_id, campaign_id=campaign_id
        )
        await self.session.execute(stmt.on_conflict_do_nothing())

    async def registrar_envios(
        self,
        *,
        campaign_id: int,
        coupon_upc: str,
        household_ids: list[int],
        entregado: dict[int, bool],
    ) -> None:
        self.session.add_all(
            CuponEnviado(
                evento_id=None,
                household_id=hid,
                coupon_upc=coupon_upc,
                campaign_id=campaign_id,
                entregado=entregado.get(hid, False),
            )
            for hid in household_ids
        )
        await self.session.flush()

    # --- cierre (tasa de retorno por grupo) ---
    async def fecha_envio(self, campaign_id: int) -> datetime | None:
        return await self.session.scalar(
            select(func.max(CuponEnviado.fecha_envio)).where(
                CuponEnviado.campaign_id == campaign_id
            )
        )

    async def retorno_por_grupo(
        self, campaign_id: int, desde: datetime
    ) -> dict[str, tuple[int, int]]:
        """`grupo -> (miembros, cuántos volvieron a comprar desde `desde`)`."""
        volvio = (
            select(Venta.venta_id)
            .where(
                Venta.household_id == CampanaCliente.household_id,
                Venta.estado == "confirmada",
                Venta.fecha_hora >= desde,
            )
            .exists()
        )
        stmt = (
            select(
                CampanaCliente.grupo,
                func.count().label("miembros"),
                func.count().filter(volvio).label("volvieron"),
            )
            .where(CampanaCliente.campaign_id == campaign_id)
            .group_by(CampanaCliente.grupo)
        )
        return {
            grupo: (int(miembros), int(volvieron))
            for grupo, miembros, volvieron in (await self.session.execute(stmt)).all()
        }

    async def crear_resultado(
        self, *, campaign_id: int, tasa_tratado, tasa_control, fecha: date
    ) -> CampanaResultado:
        resultado = CampanaResultado(
            campaign_id=campaign_id,
            tasa_retorno_tratado=tasa_tratado,
            tasa_retorno_control=tasa_control,
            fecha_calculo=fecha,
        )
        self.session.add(resultado)
        await self.session.flush()
        await self.session.refresh(resultado)  # trae el `uplift` generado en BD
        return resultado

    async def set_decision(
        self, resultado: CampanaResultado, decision: str, empleado_id: int | None
    ) -> None:
        resultado.decision = decision
        resultado.empleado_decide_id = empleado_id
        await self.session.flush()
