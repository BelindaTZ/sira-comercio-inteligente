"""CajaRepository (feature 006) — acceso a datos de apertura/cuadre de caja,
datáfonos, estándar de seguridad de pagos, reporte mensual de patrones, incidentes
de fraude, protocolo de escalamiento y umbral de merma. Sin lógica de negocio
(Principio XI). Consulta de solo lectura contra `ajustes_inventario` y
`mermas`/`venta_detalle` de 001 (plan.md, FR-010/FR-018).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.apertura_caja import AperturaCaja
from src.models.cierre_caja import CierreCaja
from src.models.configuracion_caja import CLAVE_UMBRAL_AJUSTE_ANOMALO, ConfiguracionCaja
from src.models.configuracion_seguridad_pagos import ConfiguracionSeguridadPagos
from src.models.datafono import Datafono
from src.models.incidente_fraude import IncidenteFraude
from src.models.incidente_seguridad_pago import IncidenteSeguridadPago
from src.models.politica_seguridad_pagos import PoliticaSeguridadPagos
from src.models.protocolo_escalamiento import ProtocoloEscalamiento
from src.models.umbral_merma_categoria import UmbralMermaCategoria


class CajaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def flush(self) -> None:
        await self.session.flush()

    async def refrescar(self, entity) -> None:
        await self.session.refresh(entity)

    # ============================================================ cuadre de caja (US1)
    async def apertura_vigente(self, caja_id: int, momento: datetime) -> AperturaCaja | None:
        """T006 — la apertura de caja vigente de un cuadre: la más reciente de esa
        caja con `fecha_hora <= momento` (research.md Decisión 2/3). Compartido por
        el cuadre horario (US1) y el reporte mensual (US3)."""
        stmt = (
            select(AperturaCaja)
            .where(AperturaCaja.caja_id == caja_id, AperturaCaja.fecha_hora <= momento)
            .order_by(AperturaCaja.fecha_hora.desc(), AperturaCaja.apertura_id.desc())
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def ultimo_cierre(self, caja_id: int, antes_de: datetime) -> CierreCaja | None:
        stmt = (
            select(CierreCaja)
            .where(CierreCaja.caja_id == caja_id, CierreCaja.fecha_hora < antes_de)
            .order_by(CierreCaja.fecha_hora.desc(), CierreCaja.cierre_id.desc())
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def ventas_ventana_cajero(
        self, cajero_id: int, desde: datetime, hasta: datetime
    ) -> list[dict]:
        """Ventas no anuladas del cajero con `desde < fecha_hora <= hasta`
        (research.md Decisión 1: agregación por cajero, no por caja física)."""
        rows = await self.session.execute(
            text(
                "SELECT fecha_hora, total FROM ventas "
                "WHERE cajero_id = :c AND estado <> 'anulada' "
                "AND fecha_hora > :desde AND fecha_hora <= :hasta"
            ),
            {"c": cajero_id, "desde": desde, "hasta": hasta},
        )
        return [{"fecha_hora": r.fecha_hora, "total": r.total} for r in rows]

    async def crear_apertura(
        self, *, caja_id: int, cajero_id: int, fondo_inicial: Decimal, fecha_hora: datetime
    ) -> AperturaCaja:
        apertura = AperturaCaja(
            caja_id=caja_id,
            cajero_id=cajero_id,
            fondo_inicial=fondo_inicial,
            fecha_hora=fecha_hora,
        )
        self.session.add(apertura)
        await self.session.flush()
        await self.session.refresh(apertura)
        return apertura

    async def crear_cierre(
        self,
        *,
        caja_id: int,
        cajero_id: int,
        total_esperado: Decimal,
        total_registrado: Decimal,
        fecha_hora: datetime,
    ) -> CierreCaja:
        # `fecha_hora` explícita (no server_default): dentro de una transacción,
        # CURRENT_TIMESTAMP en Postgres es la hora de INICIO de la transacción —
        # dos cuadres seguidos quedarían con la misma hora y la ventana horaria se
        # colapsaría. El service pasa `_ahora()`, la misma referencia que usa para
        # acotar la ventana.
        cierre = CierreCaja(
            caja_id=caja_id,
            cajero_id=cajero_id,
            total_esperado=total_esperado,
            total_registrado=total_registrado,
            fecha_hora=fecha_hora,
        )
        self.session.add(cierre)
        await self.session.flush()
        await self.session.refresh(cierre)  # trae `diferencia` (columna GENERATED)
        return cierre

    async def cierres_de_tienda(self, tienda_id: int, dia: date) -> list[dict]:
        """FR-005 — el estado de cuadre de todas las cajas de una tienda en un día,
        en una sola consulta (el último cierre por caja de esa fecha)."""
        rows = await self.session.execute(
            text("""
                SELECT DISTINCT ON (cc.caja_id)
                       cc.caja_id, cc.cierre_id, cc.cajero_id,
                       cc.total_esperado, cc.total_registrado, cc.diferencia, cc.fecha_hora
                FROM cierre_caja cc
                JOIN cajas c ON c.caja_id = cc.caja_id
                WHERE c.tienda_id = :t AND cc.fecha_hora::date = :dia
                ORDER BY cc.caja_id, cc.fecha_hora DESC, cc.cierre_id DESC
            """),
            {"t": tienda_id, "dia": dia},
        )
        return [dict(r._mapping) for r in rows]

    # ============================================================ datáfonos (US2)
    async def listar_datafonos(self, estado: str | None = None) -> list[Datafono]:
        stmt = select(Datafono)
        if estado is not None:
            stmt = stmt.where(Datafono.estado == estado)
        return list((await self.session.scalars(stmt.order_by(Datafono.datafono_id))).all())

    async def get_datafono(self, datafono_id: int) -> Datafono | None:
        return await self.session.get(Datafono, datafono_id)

    async def crear_datafono(
        self,
        *,
        caja_id: int,
        modelo: str | None,
        version_firmware: str | None,
        fecha_ultima_actualizacion: date | None,
        estado: str,
    ) -> Datafono:
        datafono = Datafono(
            caja_id=caja_id,
            modelo=modelo,
            version_firmware=version_firmware,
            fecha_ultima_actualizacion=fecha_ultima_actualizacion,
            estado=estado,
        )
        self.session.add(datafono)
        await self.session.flush()
        await self.session.refresh(datafono)
        return datafono

    async def caja_existe(self, caja_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text("SELECT 1 FROM cajas WHERE caja_id = :c"), {"c": caja_id}
            )
        )

    async def listar_cajas(self, tienda_id: int | None = None) -> list[dict]:
        cond = "" if tienda_id is None else "WHERE tienda_id = :t"
        rows = await self.session.execute(
            text(
                f"SELECT caja_id, tienda_id, nombre, activa FROM cajas {cond} "
                "ORDER BY tienda_id, caja_id"
            ),
            {"t": tienda_id},
        )
        return [dict(r._mapping) for r in rows]

    async def datafonos_evaluables(self) -> list[Datafono]:
        """Todos los datáfonos que no están fuera de servicio (esos no se evalúan)."""
        stmt = select(Datafono).where(Datafono.estado != "fuera_servicio")
        return list((await self.session.scalars(stmt)).all())

    async def configuracion_seguridad_vigente(self) -> ConfiguracionSeguridadPagos | None:
        stmt = (
            select(ConfiguracionSeguridadPagos)
            .order_by(
                ConfiguracionSeguridadPagos.vigente_desde.desc(),
                ConfiguracionSeguridadPagos.config_id.desc(),
            )
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def crear_configuracion_seguridad(
        self, *, version_minima_firmware: str, actualizado_por: int
    ) -> ConfiguracionSeguridadPagos:
        fila = ConfiguracionSeguridadPagos(
            version_minima_firmware=version_minima_firmware, actualizado_por=actualizado_por
        )
        self.session.add(fila)
        await self.session.flush()
        await self.session.refresh(fila)
        return fila

    # ============================================================ reporte mensual (US3)
    async def cierres_del_mes(self, mes: int, anio: int) -> list[dict]:
        """Cada cuadre del mes con su turno (apertura vigente) resuelto en SQL
        (research.md Decisión 3)."""
        rows = await self.session.execute(
            text("""
                SELECT cc.cajero_id, cc.diferencia,
                       ac.apertura_id,
                       ac.fecha_hora::date AS fecha_turno
                FROM cierre_caja cc
                JOIN LATERAL (
                    SELECT a.apertura_id, a.fecha_hora
                    FROM apertura_caja a
                    WHERE a.caja_id = cc.caja_id AND a.fecha_hora <= cc.fecha_hora
                    ORDER BY a.fecha_hora DESC, a.apertura_id DESC
                    LIMIT 1
                ) ac ON true
                WHERE EXTRACT(MONTH FROM cc.fecha_hora) = :mes
                  AND EXTRACT(YEAR FROM cc.fecha_hora) = :anio
            """),
            {"mes": mes, "anio": anio},
        )
        return [
            {
                "cajero_id": r.cajero_id,
                "apertura_id": r.apertura_id,
                "fecha_turno": r.fecha_turno,
                "diferencia": r.diferencia,
            }
            for r in rows
        ]

    async def ajustes_negativos_del_mes(self, mes: int, anio: int) -> list[dict]:
        rows = await self.session.execute(
            text("""
                SELECT ajuste_id, product_id, tienda_id, diferencia, empleado_id, fecha
                FROM ajustes_inventario
                WHERE diferencia < 0
                  AND EXTRACT(MONTH FROM fecha) = :mes
                  AND EXTRACT(YEAR FROM fecha) = :anio
                ORDER BY fecha, ajuste_id
            """),
            {"mes": mes, "anio": anio},
        )
        return [dict(r._mapping) for r in rows]

    async def umbral_ajuste_anomalo(self) -> Decimal:
        fila = await self.session.get(ConfiguracionCaja, CLAVE_UMBRAL_AJUSTE_ANOMALO)
        return Decimal(str(fila.valor)) if fila is not None else Decimal("10")

    # ============================================================ incidentes (US3/US4)
    async def crear_incidente(
        self,
        *,
        empleado_id: int,
        descripcion: str,
        cierre_id: int | None,
        ajuste_id: int | None,
    ) -> IncidenteFraude:
        incidente = IncidenteFraude(
            empleado_id=empleado_id,
            descripcion=descripcion,
            cierre_id=cierre_id,
            ajuste_id=ajuste_id,
        )
        self.session.add(incidente)
        await self.session.flush()
        await self.session.refresh(incidente)
        return incidente

    async def get_incidente(self, incidente_id: int) -> IncidenteFraude | None:
        return await self.session.get(IncidenteFraude, incidente_id)

    async def listar_incidentes(
        self, *, estado: str | None = None, tienda_id: int | None = None
    ) -> list[IncidenteFraude]:
        stmt = select(IncidenteFraude)
        if estado is not None:
            stmt = stmt.where(IncidenteFraude.estado == estado)
        if tienda_id is not None:
            # FR: el Encargado sólo ve los incidentes de empleados de su tienda.
            empleado_ids = (
                await self.session.execute(
                    text("SELECT empleado_id FROM empleados WHERE tienda_id = :t"),
                    {"t": tienda_id},
                )
            ).scalars().all()
            stmt = stmt.where(IncidenteFraude.empleado_id.in_(empleado_ids or [-1]))
        return list(
            (await self.session.scalars(stmt.order_by(IncidenteFraude.incidente_id.desc()))).all()
        )

    async def nombres_de_empleados(self, ids: list[int]) -> dict[int, str | None]:
        if not ids:
            return {}
        rows = await self.session.execute(
            text("SELECT empleado_id, nombre FROM empleados WHERE empleado_id = ANY(:ids)"),
            {"ids": ids},
        )
        return {r.empleado_id: r.nombre for r in rows}

    # ============================================================ protocolo (US4)
    async def protocolo_vigente(self) -> ProtocoloEscalamiento | None:
        stmt = (
            select(ProtocoloEscalamiento)
            .order_by(
                ProtocoloEscalamiento.fecha_creacion.desc(),
                ProtocoloEscalamiento.protocolo_id.desc(),
            )
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def crear_protocolo(self, *, texto: str, definido_por: int) -> ProtocoloEscalamiento:
        fila = ProtocoloEscalamiento(texto=texto, definido_por=definido_por)
        self.session.add(fila)
        await self.session.flush()
        await self.session.refresh(fila)
        return fila

    async def listar_protocolos(self) -> list[ProtocoloEscalamiento]:
        """Historial completo, más reciente primero (append-only, FR-012)."""
        stmt = select(ProtocoloEscalamiento).order_by(
            ProtocoloEscalamiento.fecha_creacion.desc(),
            ProtocoloEscalamiento.protocolo_id.desc(),
        )
        return list((await self.session.scalars(stmt)).all())

    # ============================================================ umbral de merma (US5)
    async def listar_umbrales(self) -> list[UmbralMermaCategoria]:
        stmt = select(UmbralMermaCategoria).order_by(UmbralMermaCategoria.product_category)
        return list((await self.session.scalars(stmt)).all())

    async def get_umbral(self, product_category: str) -> UmbralMermaCategoria | None:
        return await self.session.get(UmbralMermaCategoria, product_category)

    async def upsert_umbral(
        self, *, product_category: str, porcentaje_umbral: Decimal, definido_por: int
    ) -> UmbralMermaCategoria:
        stmt = pg_insert(UmbralMermaCategoria).values(
            product_category=product_category,
            porcentaje_umbral=porcentaje_umbral,
            definido_por=definido_por,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["product_category"],
            set_={
                "porcentaje_umbral": stmt.excluded.porcentaje_umbral,
                "definido_por": stmt.excluded.definido_por,
                "fecha_actualizacion": func.current_timestamp(),
            },
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.get_umbral(product_category)  # type: ignore[return-value]

    async def valor_merma_semana(
        self, tienda_id: int, semana: int, anio: int
    ) -> dict[str, Decimal]:
        rows = await self.session.execute(
            text("""
                SELECT p.product_category AS cat, COALESCE(SUM(m.valor), 0)::numeric AS valor
                FROM mermas m
                JOIN productos p ON p.product_id = m.product_id
                WHERE m.tienda_id = :t
                  AND EXTRACT(WEEK FROM m.fecha) = :sem
                  AND EXTRACT(ISOYEAR FROM m.fecha) = :anio
                GROUP BY p.product_category
            """),
            {"t": tienda_id, "sem": semana, "anio": anio},
        )
        return {r.cat: Decimal(str(r.valor)) for r in rows if r.cat is not None}

    # ============================================================ feature 007
    async def marcar_estado_datafono(self, datafono: Datafono, estado: str) -> Datafono:
        datafono.estado = estado
        await self.session.flush()
        return datafono

    async def crear_incidente_seguridad(
        self, *, datafono_id: int | None, registrado_por: int, descripcion: str
    ) -> IncidenteSeguridadPago:
        incidente = IncidenteSeguridadPago(
            datafono_id=datafono_id, registrado_por=registrado_por, descripcion=descripcion
        )
        self.session.add(incidente)
        await self.session.flush()
        await self.session.refresh(incidente)
        return incidente

    async def get_incidente_seguridad(self, incidente_id: int) -> IncidenteSeguridadPago | None:
        return await self.session.get(IncidenteSeguridadPago, incidente_id)

    async def listar_incidentes_seguridad(
        self, estado: str | None = None
    ) -> list[IncidenteSeguridadPago]:
        stmt = select(IncidenteSeguridadPago)
        if estado is not None:
            stmt = stmt.where(IncidenteSeguridadPago.estado == estado)
        stmt = stmt.order_by(IncidenteSeguridadPago.incidente_seguridad_id.desc())
        return list((await self.session.scalars(stmt)).all())

    async def contar_incidentes_seguridad(
        self, desde: date | None, hasta: date | None
    ) -> int:
        stmt = select(func.count(IncidenteSeguridadPago.incidente_seguridad_id))
        if desde is not None:
            stmt = stmt.where(IncidenteSeguridadPago.fecha_hora >= desde)
        if hasta is not None:
            # `hasta` inclusivo por día
            stmt = stmt.where(func.date(IncidenteSeguridadPago.fecha_hora) <= hasta)
        return int(await self.session.scalar(stmt) or 0)

    async def politica_vigente(self) -> PoliticaSeguridadPagos | None:
        stmt = (
            select(PoliticaSeguridadPagos)
            .order_by(
                PoliticaSeguridadPagos.fecha_creacion.desc(),
                PoliticaSeguridadPagos.politica_id.desc(),
            )
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def get_politica(self, politica_id: int) -> PoliticaSeguridadPagos | None:
        return await self.session.get(PoliticaSeguridadPagos, politica_id)

    async def listar_politicas(self) -> list[PoliticaSeguridadPagos]:
        """Historial completo, más reciente primero (append-only, FR-014)."""
        stmt = select(PoliticaSeguridadPagos).order_by(
            PoliticaSeguridadPagos.fecha_creacion.desc(),
            PoliticaSeguridadPagos.politica_id.desc(),
        )
        return list((await self.session.scalars(stmt)).all())

    async def crear_politica(self, *, texto: str, definido_por: int) -> PoliticaSeguridadPagos:
        fila = PoliticaSeguridadPagos(texto=texto, definido_por=definido_por)
        self.session.add(fila)
        await self.session.flush()
        await self.session.refresh(fila)
        return fila

    async def valor_ventas_semana(
        self, tienda_id: int, semana: int, anio: int
    ) -> dict[str, Decimal]:
        rows = await self.session.execute(
            text("""
                SELECT p.product_category AS cat,
                       COALESCE(SUM(vd.sales_value * vd.cantidad), 0)::numeric AS valor
                FROM venta_detalle vd
                JOIN ventas v ON v.venta_id = vd.venta_id
                JOIN productos p ON p.product_id = vd.product_id
                WHERE v.tienda_id = :t AND v.semana = :sem AND v.estado = 'confirmada'
                GROUP BY p.product_category
            """),
            {"t": tienda_id, "sem": semana},
        )
        return {r.cat: Decimal(str(r.valor)) for r in rows if r.cat is not None}
