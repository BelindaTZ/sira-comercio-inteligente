"""TrasladosService — regla de negocio del ciclo de traslados entre tiendas
(feature 012, OT-2.5).

Reutiliza el mecanismo de stock de 001 (`InventarioRepository`): descuento FIFO de
lotes en origen al despachar, alta de lote en destino al recibir, y una fila en
`movimientos_inventario` por cada movimiento — nunca un contador en memoria
(Principio II). El frontend no replica ninguno de estos cálculos (Principio V).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import text

from src.models.lote import Lote
from src.models.movimiento_inventario import MovimientoInventario
from src.models.traslado_stock import TrasladoStock
from src.modules.inventario.repository import InventarioRepository
from src.modules.traslados.repository import TrasladosRepository
from src.modules.traslados.schemas import TrasladoCreate
from src.shared.exceptions import ConflictError, ForbiddenError, NotFoundError
from src.shared.inventario_fifo import ordenar_lotes_fifo_fefo

_JEFE_OPS = "Jefe_Operaciones"
_REF_TABLA = "traslados_stock"


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TrasladosService:
    def __init__(self, repo: TrasladosRepository) -> None:
        self.repo = repo
        self.inv = InventarioRepository(repo.session)

    # ============================================================ US1: disponibilidad
    async def disponibilidad_sucursales(self, product_id: int) -> dict:
        if await self.inv.get_producto(product_id) is None:
            raise NotFoundError(f"Producto {product_id} no existe")
        return {
            "product_id": product_id,
            "disponibilidad": await self.repo.disponibilidad_sucursales(product_id),
        }

    # ============================================================ US2: solicitud
    async def registrar_solicitud(self, data: TrasladoCreate, empleado_id: int) -> TrasladoStock:
        """FR-003 — alta en estado `solicitado`. La validación de stock aquí es
        optimista/informativa; la autoritativa ocurre al aprobar (research.md
        Decisión 3)."""
        if await self.inv.get_producto(data.product_id) is None:
            raise NotFoundError(f"Producto {data.product_id} no existe")
        return await self.repo.crear(
            TrasladoStock(
                product_id=data.product_id,
                tienda_origen_id=data.tienda_origen_id,
                tienda_destino_id=data.tienda_destino_id,
                cantidad=data.cantidad,
                estado="solicitado",
                empleado_id=empleado_id,
            )
        )

    async def listar(
        self,
        *,
        estado: str | None,
        tienda_origen_id: int | None,
        rol: str | None,
        tienda_actor: int | None,
    ) -> list[TrasladoStock]:
        """FR-004 (listado de pendientes de resolución). El `Encargado_Tienda`
        queda limitado a los traslados cuya tienda origen es la suya."""
        if rol != _JEFE_OPS:
            if tienda_origen_id is not None and tienda_origen_id != tienda_actor:
                raise ForbiddenError(
                    "El Encargado de Tienda sólo ve los traslados de su propia tienda origen"
                )
            tienda_origen_id = tienda_actor
        return await self.repo.listar(estado=estado, tienda_origen_id=tienda_origen_id)

    # ============================================================ US2: resolución
    async def resolver(
        self,
        traslado_id: int,
        *,
        decision: str,
        motivo: str | None,
        rol: str | None,
        empleado_actor: int,
        tienda_actor: int | None,
    ) -> TrasladoStock:
        """FR-004/FR-005/FR-006 — aprobar (→ `en_transito`, descuenta y despacha) o
        rechazar (→ `rechazado`, sin efecto sobre inventario)."""
        traslado = await self.repo.get_for_update(traslado_id)
        if traslado is None:
            raise NotFoundError(f"Traslado {traslado_id} no existe")
        if traslado.estado != "solicitado":
            raise ConflictError(
                f"El traslado {traslado_id} ya no está 'solicitado' (está '{traslado.estado}')"
            )
        if rol != _JEFE_OPS and tienda_actor != traslado.tienda_origen_id:
            raise ForbiddenError(
                "Sólo el Encargado de la tienda origen (o el Jefe de Operaciones) resuelve"
            )

        traslado.resuelto_por = empleado_actor
        traslado.fecha_resolucion = _ahora()

        if decision == "rechazar":
            traslado.estado = "rechazado"
            await self.repo.flush()
            return traslado

        # aprobar → revalidación autoritativa de stock + despacho, misma transacción
        inv = await self.inv.get_inventario_for_update(
            traslado.product_id, traslado.tienda_origen_id
        )
        disponible = inv.cantidad_disponible if inv else 0
        if disponible < traslado.cantidad:
            raise ConflictError(
                f"Stock insuficiente en la tienda origen: hay {disponible}, "
                f"se solicitaron {traslado.cantidad}",
                details={
                    "stock_disponible": disponible,
                    "cantidad_solicitada": traslado.cantidad,
                },
            )

        inv.cantidad_disponible -= traslado.cantidad
        await self._despachar_fifo(traslado)
        traslado.estado = "en_transito"
        await self.repo.flush()
        return traslado

    async def _despachar_fifo(self, traslado: TrasladoStock) -> None:
        """Descuenta la cantidad de los lotes de origen en orden FIFO/FEFO y deja
        una fila `traslado_salida` en `movimientos_inventario` por cada lote tocado
        (con su `lote_id`, para heredar la fecha de vencimiento en la recepción)."""
        restante = traslado.cantidad
        lotes = ordenar_lotes_fifo_fefo(
            await self.inv.lotes_con_saldo_for_update(
                traslado.product_id, traslado.tienda_origen_id
            )
        )
        for lote in lotes:
            if restante == 0:
                break
            toma = min(restante, lote.cantidad_disponible)
            lote.cantidad_disponible -= toma
            restante -= toma
            self.inv.agregar(
                MovimientoInventario(
                    product_id=traslado.product_id,
                    tienda_id=traslado.tienda_origen_id,
                    tipo="traslado_salida",
                    cantidad=toma,
                    referencia_tabla=_REF_TABLA,
                    referencia_id=traslado.traslado_id,
                    lote_id=lote.lote_id,
                )
            )
        if restante > 0:
            # `inventario` ya validó que hay saldo; si los lotes no lo reflejan
            # (drift por ajustes previos), el remanente sale sin lote asociado.
            self.inv.agregar(
                MovimientoInventario(
                    product_id=traslado.product_id,
                    tienda_id=traslado.tienda_origen_id,
                    tipo="traslado_salida",
                    cantidad=restante,
                    referencia_tabla=_REF_TABLA,
                    referencia_id=traslado.traslado_id,
                )
            )

    # ============================================================ US3: recepción
    async def confirmar_recepcion(
        self,
        traslado_id: int,
        *,
        rol: str | None,
        empleado_actor: int,
        tienda_actor: int | None,
    ) -> TrasladoStock:
        """FR-007/FR-008/FR-010 — suma la cantidad al stock de destino, crea el
        lote de destino heredando la fecha de vencimiento del lote de origen
        consumido, y deja una fila `traslado_entrada`."""
        traslado = await self.repo.get_for_update(traslado_id)
        if traslado is None:
            raise NotFoundError(f"Traslado {traslado_id} no existe")
        if traslado.estado != "en_transito":
            raise ConflictError(
                f"El traslado {traslado_id} no está 'en_transito' (está '{traslado.estado}')"
            )
        if rol != _JEFE_OPS and tienda_actor != traslado.tienda_destino_id:
            raise ForbiddenError(
                "Sólo el Encargado de la tienda destino (o el Jefe de Operaciones) confirma"
            )

        vencimiento = await self._vencimiento_heredado(traslado.traslado_id)
        await self.inv.upsert_inventario(
            traslado.product_id, traslado.tienda_destino_id, traslado.cantidad
        )
        lote_destino = Lote(
            product_id=traslado.product_id,
            tienda_id=traslado.tienda_destino_id,
            cantidad_recibida=traslado.cantidad,
            cantidad_disponible=traslado.cantidad,
            fecha_vencimiento=vencimiento,
        )
        self.inv.agregar(lote_destino)
        await self.inv.flush()
        self.inv.agregar(
            MovimientoInventario(
                product_id=traslado.product_id,
                tienda_id=traslado.tienda_destino_id,
                tipo="traslado_entrada",
                cantidad=traslado.cantidad,
                referencia_tabla=_REF_TABLA,
                referencia_id=traslado.traslado_id,
                lote_id=lote_destino.lote_id,
            )
        )
        traslado.estado = "recibido"
        traslado.recibido_por = empleado_actor
        traslado.fecha_recepcion = _ahora()
        await self.repo.flush()
        return traslado

    async def _vencimiento_heredado(self, traslado_id: int) -> date | None:
        """La fecha de vencimiento más próxima entre los lotes de origen consumidos
        por el despacho (FR-010). `None` si ninguno tenía fecha (no perecedero)."""
        return await self.repo.session.scalar(
            text("""
                SELECT MIN(l.fecha_vencimiento)
                FROM movimientos_inventario m
                JOIN lotes l ON l.lote_id = m.lote_id
                WHERE m.referencia_tabla = :ref
                  AND m.referencia_id = :tid
                  AND m.tipo = 'traslado_salida'
            """),
            {"ref": _REF_TABLA, "tid": traslado_id},
        )

    # ============================================================ US2/US3: cancelación
    async def cancelar(
        self, traslado_id: int, *, rol: str | None, empleado_actor: int
    ) -> TrasladoStock:
        """FR-009 — sólo mientras siga `solicitado`; sin efecto sobre inventario."""
        traslado = await self.repo.get_for_update(traslado_id)
        if traslado is None:
            raise NotFoundError(f"Traslado {traslado_id} no existe")
        if traslado.estado != "solicitado":
            raise ConflictError(
                f"Sólo se cancela un traslado 'solicitado' (está '{traslado.estado}')"
            )
        if rol != _JEFE_OPS and empleado_actor != traslado.empleado_id:
            raise ForbiddenError(
                "Sólo el empleado solicitante (o el Jefe de Operaciones) cancela la solicitud"
            )
        traslado.estado = "cancelado"
        traslado.fecha_cancelacion = _ahora()
        await self.repo.flush()
        return traslado

    # ============================================================ US1/US3: reporte
    async def reporte_semanal(self, desde: date, hasta: date) -> list[TrasladoStock]:
        """FR-012 — traslados del periodo. El router marca `pendiente_confirmacion`
        para los que quedaron `en_transito` sin recibir."""
        return await self.repo.listar_periodo(desde, hasta)
