"""InventarioService — regla de negocio de recepción, ajuste y merma (US2).

Toda mutación de stock pasa por aquí y deja rastro en `movimientos_inventario`
(Principio II). El frontend nunca replica estos cálculos.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from src.core.config import settings
from src.integrations import sendgrid_client
from src.models.ajuste_inventario import AjusteInventario
from src.models.alerta_inventario import AlertaInventario
from src.models.evento_quiebre_stock import EventoQuiebreStock
from src.models.lote import Lote
from src.models.merma import Merma
from src.models.movimiento_inventario import MovimientoInventario
from src.models.recepcion_mercaderia import RecepcionMercaderia
from src.models.stock_maximo_categoria import StockMaximoCategoria
from src.models.verificacion_anaquel import VerificacionAnaquel
from src.modules.inventario.repository import InventarioRepository
from src.modules.inventario.schemas import (
    AjusteIn,
    AtenderAlertaIn,
    MermaIn,
    QuiebreIn,
    RecepcionIn,
    StockMaximoIn,
    ValidarMermaIn,
    VerificacionAnaquelIn,
)
from src.shared.exceptions import BusinessRuleError, ConflictError, NotFoundError
from src.shared.inventario_fifo import ordenar_lotes_fifo_fefo
from src.shared.reposicion import punto_reposicion, punto_reposicion_desde_ventas

logger = logging.getLogger("sira.inventario")


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _forecasting_service(session):
    """Instancia el servicio de pronóstico de 004 sobre la misma sesión, con
    import diferido para no acoplar `inventario` a `forecasting` a nivel de módulo."""
    from src.modules.forecasting.repository import ForecastingRepository
    from src.modules.forecasting.service import ForecastingService

    return ForecastingService(ForecastingRepository(session))


class InventarioService:
    def __init__(self, repo: InventarioRepository) -> None:
        self.repo = repo

    # ---------------------------------------------------------------- recepción
    async def registrar_recepcion(self, data: RecepcionIn, empleado_id: int) -> dict:
        orden = await self.repo.get_orden_for_update(data.orden_id)
        if orden is None:
            raise NotFoundError(f"Orden de compra {data.orden_id} no existe")
        if orden.estado not in ("aprobada", "confirmada"):
            raise BusinessRuleError(
                "Sólo se recibe contra una orden aprobada o confirmada por el "
                f"proveedor (está '{orden.estado}')"
            )
        if orden.tienda_id != data.tienda_id:
            raise BusinessRuleError("La tienda de la recepción no coincide con la de la orden")

        lote = Lote(
            product_id=data.product_id,
            tienda_id=data.tienda_id,
            cantidad_recibida=data.cantidad,
            cantidad_disponible=data.cantidad,
            fecha_vencimiento=data.fecha_vencimiento,
            codigo_lote_proveedor=data.codigo_lote_proveedor,
        )
        self.repo.agregar(lote)
        await self.repo.flush()

        recepcion = RecepcionMercaderia(
            orden_id=data.orden_id,
            lote_id=lote.lote_id,
            tienda_id=data.tienda_id,
            empleado_id=empleado_id,
        )
        self.repo.agregar(recepcion)
        await self.repo.flush()

        inv = await self.repo.upsert_inventario(data.product_id, data.tienda_id, data.cantidad)
        self.repo.agregar(
            MovimientoInventario(
                product_id=data.product_id,
                tienda_id=data.tienda_id,
                tipo="entrada",
                cantidad=data.cantidad,
                referencia_tabla="recepcion_mercaderia",
                referencia_id=recepcion.recepcion_id,
                lote_id=lote.lote_id,
            )
        )
        # la orden se cierra sólo cuando todas sus líneas tienen recepción
        if await self.repo.lineas_sin_recibir(data.orden_id) == 0:
            orden.estado = "recibida"
        await self.repo.flush()

        # Ronda 9 (FR-038): si la recepción deja el stock por encima del máximo
        # vigente de su categoría, genera una alerta `exceso_stock` — sin bloquear.
        await self._chequear_exceso_stock(data.product_id, data.tienda_id, inv.cantidad_disponible)

        return {
            "recepcion_id": recepcion.recepcion_id,
            "lote_id": lote.lote_id,
            "orden_id": data.orden_id,
            "product_id": data.product_id,
            "tienda_id": data.tienda_id,
            "cantidad": data.cantidad,
            "fecha_vencimiento": data.fecha_vencimiento,
            "stock_disponible": inv.cantidad_disponible,
        }

    async def _chequear_exceso_stock(
        self, product_id: int, tienda_id: int, disponible: int
    ) -> None:
        producto = await self.repo.get_producto(product_id)
        if producto is None or not producto.product_category:
            return
        maximo = await self.repo.get_stock_maximo(producto.product_category, tienda_id)
        if maximo is None or disponible <= maximo.cantidad_maxima:
            return
        if await self.repo.alerta_pendiente(product_id, tienda_id, "exceso_stock"):
            return
        self.repo.agregar(
            AlertaInventario(
                tipo="exceso_stock",
                product_id=product_id,
                tienda_id=tienda_id,
                estado="pendiente",
            )
        )
        await self.repo.flush()

    # ------------------------------------------------------------------ ajuste
    async def registrar_ajuste(self, data: AjusteIn) -> dict:
        inv = await self.repo.get_inventario_for_update(data.product_id, data.tienda_id)
        cantidad_sistema = inv.cantidad_disponible if inv else 0

        ajuste = AjusteInventario(
            product_id=data.product_id,
            tienda_id=data.tienda_id,
            cantidad_sistema=cantidad_sistema,
            cantidad_fisica=data.cantidad_fisica,
            empleado_id=data.empleado_id,
            motivo=data.motivo,
            observaciones=data.observaciones,
        )
        self.repo.agregar(ajuste)
        await self.repo.flush()
        await self.repo.refrescar(ajuste)  # trae `diferencia` (columna generada en BD)

        diferencia = ajuste.diferencia
        if inv is None:
            inv = await self.repo.upsert_inventario(
                data.product_id, data.tienda_id, data.cantidad_fisica
            )
        else:
            inv.cantidad_disponible = data.cantidad_fisica

        if diferencia != 0:
            self.repo.agregar(
                MovimientoInventario(
                    product_id=data.product_id,
                    tienda_id=data.tienda_id,
                    tipo="ajuste",
                    cantidad=diferencia,
                    referencia_tabla="ajustes_inventario",
                    referencia_id=ajuste.ajuste_id,
                )
            )
        # Un faltante se reparte contra los lotes (FIFO); un sobrante físico no se
        # puede atribuir a un lote concreto (limitación del esquema base) y queda
        # sólo en el agregado.
        if diferencia < 0:
            await self._descontar_lotes_fifo(
                data.product_id, data.tienda_id, -diferencia, permitir_parcial=True
            )
        await self.repo.flush()

        return {
            "ajuste_id": ajuste.ajuste_id,
            "product_id": data.product_id,
            "tienda_id": data.tienda_id,
            "cantidad_sistema": cantidad_sistema,
            "cantidad_fisica": data.cantidad_fisica,
            "diferencia": diferencia,
            "stock_disponible": inv.cantidad_disponible,
        }

    # ------------------------------------------------------------------- merma
    async def registrar_merma(self, data: MermaIn) -> Merma:
        producto = await self.repo.get_producto(data.product_id)
        if producto is None:
            raise NotFoundError(f"Producto {data.product_id} no existe")

        if data.lote_id is not None:
            lote = await self.repo.get_lote_for_update(data.lote_id)
            if lote is None:
                raise NotFoundError(f"Lote {data.lote_id} no existe")
            if lote.product_id != data.product_id or lote.tienda_id != data.tienda_id:
                raise BusinessRuleError("El lote no corresponde al producto/tienda de la merma")

        costo = Decimal(str(producto.costo)) if producto.costo is not None else Decimal("0")
        merma = Merma(
            product_id=data.product_id,
            tienda_id=data.tienda_id,
            lote_id=data.lote_id,
            cantidad=data.cantidad,
            causa=data.causa,
            valor=(costo * data.cantidad).quantize(Decimal("0.01")),
            empleado_id=data.empleado_id,
            estado_validacion="pendiente",
            destino=data.destino,
            observaciones=data.observaciones,
        )
        self.repo.agregar(merma)
        await self.repo.flush()
        return merma

    async def validar_merma(self, merma_id: int, data: ValidarMermaIn) -> Merma:
        merma = await self.repo.get_merma_for_update(merma_id)
        if merma is None:
            raise NotFoundError(f"Merma {merma_id} no existe")
        if merma.estado_validacion != "pendiente":
            raise BusinessRuleError(f"La merma {merma_id} ya fue {merma.estado_validacion}")

        merma.estado_validacion = data.decision
        merma.empleado_valida_id = data.empleado_id
        merma.fecha_validacion = _ahora()

        # FR-019: sólo una merma validada descuenta stock; una rechazada no altera nada.
        if data.decision == "validada":
            inv = await self.repo.get_inventario_for_update(merma.product_id, merma.tienda_id)
            if inv is None or inv.cantidad_disponible < merma.cantidad:
                raise ConflictError(
                    f"Stock insuficiente para dar de baja {merma.cantidad} unidades"
                )
            if merma.lote_id is not None:
                lote = await self.repo.get_lote_for_update(merma.lote_id)
                if lote is None or lote.cantidad_disponible < merma.cantidad:
                    raise ConflictError("El lote indicado no tiene saldo suficiente")
                lote.cantidad_disponible -= merma.cantidad
            else:
                await self._descontar_lotes_fifo(
                    merma.product_id, merma.tienda_id, merma.cantidad, permitir_parcial=False
                )
            inv.cantidad_disponible -= merma.cantidad
            self.repo.agregar(
                MovimientoInventario(
                    product_id=merma.product_id,
                    tienda_id=merma.tienda_id,
                    tipo="salida",
                    cantidad=merma.cantidad,
                    referencia_tabla="mermas",
                    referencia_id=merma.merma_id,
                    lote_id=merma.lote_id,
                )
            )

        await self.repo.flush()
        return merma

    async def listar_mermas(
        self,
        *,
        tienda_id: int | None = None,
        causa: str | None = None,
        estado_validacion: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        return await self.repo.listar_mermas(
            tienda_id=tienda_id,
            causa=causa,
            estado_validacion=estado_validacion,
            search=search,
            limit=limit,
        )

    async def kpis_merma(self, tienda_id: int) -> dict:
        return await self.repo.kpis_merma(tienda_id)

    # ------------------------------------------------------------------- lotes
    async def listar_lotes(
        self,
        params,
        *,
        product_id: int | None = None,
        tienda_id: int | None = None,
        proximos_a_vencer: bool = False,
        dias: int = 7,
        search: str | None = None,
    ):
        vence_antes_de = date.today() + timedelta(days=dias) if proximos_a_vencer else None
        stmt = self.repo.lotes_query(
            product_id=product_id,
            tienda_id=tienda_id,
            vence_antes_de=vence_antes_de,
            search=search,
        )
        page = await self.repo.paginate(
            params, stmt=stmt, order_by=Lote.fecha_vencimiento.asc().nulls_last()
        )
        hoy = date.today()
        nombres = await self.repo.nombres_de_productos([lo.product_id for lo in page.items])
        items = [
            {
                "lote_id": lo.lote_id,
                "product_id": lo.product_id,
                "producto_nombre": nombres.get(lo.product_id),
                "tienda_id": lo.tienda_id,
                "cantidad_recibida": lo.cantidad_recibida,
                "cantidad_disponible": lo.cantidad_disponible,
                "fecha_vencimiento": lo.fecha_vencimiento,
                "codigo_lote_proveedor": lo.codigo_lote_proveedor,
                "dias_para_vencer": (
                    (lo.fecha_vencimiento - hoy).days if lo.fecha_vencimiento else None
                ),
            }
            for lo in page.items
        ]
        return {"items": items, "total": page.total, "page": page.page, "size": page.size}

    # ---------------------------------------------------------------- helpers
    async def _descontar_lotes_fifo(
        self, product_id: int, tienda_id: int, cantidad: int, *, permitir_parcial: bool
    ) -> None:
        restante = cantidad
        for lote in ordenar_lotes_fifo_fefo(
            await self.repo.lotes_con_saldo_for_update(product_id, tienda_id)
        ):
            if restante == 0:
                break
            toma = min(restante, lote.cantidad_disponible)
            lote.cantidad_disponible -= toma
            restante -= toma
        if restante > 0 and not permitir_parcial:
            raise BusinessRuleError(
                f"Los lotes del producto {product_id} no cubren {cantidad} unidades"
            )

    # ============================================================ US3: alertas
    async def ejecutar_job_reposicion(self, tienda_id: int | None = None) -> list[dict]:
        """FR-020: recalcula el punto de reposición dinámico de cada (producto,
        tienda) y genera una alerta `reposicion` si el stock cae por debajo."""
        ventana = int(await self.repo.config("reposicion_ventana_dias", Decimal("14")))
        lead_time = float(await self.repo.config("lead_time_dias_default", Decimal("7")))
        seguridad = float(await self.repo.config("stock_seguridad_pct", Decimal("0.20")))
        desde = _ahora() - timedelta(days=ventana)

        # feature 004: si hay un pronóstico vigente del modelo en producción, la
        # demanda proyectada reemplaza a la rotación reciente como base del cálculo
        # (FR-007). Sin pronóstico, se usa el respaldo de 001 sin interrupción (FR-008).
        forecasting = _forecasting_service(self.repo.session)

        generadas: list[dict] = []
        for product_id, t_id in await self.repo.pares_inventario(tienda_id):
            pronostico = await forecasting.demanda_semanal_vigente(product_id, t_id)
            if pronostico is not None:
                punto = punto_reposicion(pronostico / 7.0, lead_time, seguridad)
                origen = "modelo_pronostico"
            else:
                vendidas = await self.repo.unidades_vendidas(product_id, t_id, desde)
                punto = punto_reposicion_desde_ventas(vendidas, ventana, lead_time, seguridad)
                origen = "rotacion_reciente"

            inv = await self.repo.get_inventario_for_update(product_id, t_id)
            if inv is None:
                continue
            # El punto dinámico reemplaza al mínimo operativo SÓLO cuando hay señal
            # de demanda (`punto > 0`). Con un dataset histórico sin ventas recientes
            # el punto es 0 para todo — no se rebaja el umbral ya configurado, que
            # dejaría la alerta de quiebre sin efecto (Principio VII / arranque en frío).
            if punto > 0:
                inv.cantidad_minima = punto

            if (
                punto > 0
                and inv.cantidad_disponible < punto
                and not await self.repo.alerta_pendiente(product_id, t_id, "reposicion")
            ):
                alerta = AlertaInventario(
                    tipo="reposicion",
                    product_id=product_id,
                    tienda_id=t_id,
                    estado="pendiente",
                    origen_calculo=origen,
                )
                self.repo.agregar(alerta)
                generadas.append(
                    {
                        "product_id": product_id,
                        "tienda_id": t_id,
                        "punto_reposicion": punto,
                        "origen_calculo": origen,
                    }
                )
        await self.repo.flush()
        return generadas

    async def ejecutar_job_vencimiento(self, tienda_id: int | None = None) -> list[dict]:
        """FR-016: alerta de lotes perecederos próximos a vencer (umbral configurable)."""
        umbral_dias = int(await self.repo.config("vencimiento_umbral_dias", Decimal("15")))
        umbral = date.today() + timedelta(days=umbral_dias)

        generadas: list[dict] = []
        for lote in await self.repo.lotes_perecederos_venciendo(umbral, tienda_id):
            if await self.repo.alerta_vencimiento_pendiente_lote(lote.lote_id):
                continue
            self.repo.agregar(
                AlertaInventario(
                    tipo="vencimiento",
                    product_id=lote.product_id,
                    tienda_id=lote.tienda_id,
                    lote_id=lote.lote_id,
                    estado="pendiente",
                )
            )
            generadas.append({"lote_id": lote.lote_id, "fecha_vencimiento": lote.fecha_vencimiento})
        await self.repo.flush()
        return generadas

    async def atender_alerta(self, alerta_id: int, data: AtenderAlertaIn) -> AlertaInventario:
        """FR-021: marca una alerta como atendida. El índice único parcial de BD
        impide que exista una segunda alerta activa del mismo tipo/producto/tienda."""
        alerta = await self.repo.get_alerta_for_update(alerta_id)
        if alerta is None:
            raise NotFoundError(f"Alerta {alerta_id} no existe")
        if alerta.estado != "pendiente":
            raise BusinessRuleError(f"La alerta {alerta_id} ya fue atendida")
        alerta.estado = "atendida"
        alerta.fecha_atendida = _ahora()
        alerta.empleado_atiende_id = data.empleado_id
        await self.repo.flush()
        return alerta

    async def listar_alertas(self, params, *, tipo=None, estado=None, tienda_id=None, search=None):
        stmt = self.repo.alertas_query(
            tipo=tipo, estado=estado, tienda_id=tienda_id, search=search
        )
        page = await self.repo.paginate(
            params, stmt=stmt, order_by=AlertaInventario.fecha_generada.desc()
        )
        nombres = await self.repo.nombres_de_productos([a.product_id for a in page.items])
        for alerta in page.items:
            alerta.producto_nombre = nombres.get(alerta.product_id)
        return page

    # =========================================================== US3: quiebre
    async def registrar_quiebre(self, data: QuiebreIn) -> EventoQuiebreStock:
        """FR-022 (append-only). Ronda 10 (FR-043): si el producto es clase A,
        marca `es_alta_demanda` y notifica de inmediato al Jefe de Operaciones."""
        producto = await self.repo.get_producto(data.product_id)
        if producto is None:
            raise NotFoundError(f"Producto {data.product_id} no existe")

        es_alta_demanda = producto.clasificacion_abc == "A"
        evento = EventoQuiebreStock(
            product_id=data.product_id,
            tienda_id=data.tienda_id,
            empleado_id=data.empleado_id,
            demanda_estimada_no_satisfecha=data.demanda_estimada_no_satisfecha,
            es_alta_demanda=es_alta_demanda,
        )
        self.repo.agregar(evento)
        await self.repo.flush()

        if es_alta_demanda:
            self._notificar_alta_demanda(evento)
        return evento

    def _notificar_alta_demanda(self, evento: EventoQuiebreStock) -> None:
        """El registro de negocio ya está persistido; la notificación no lo bloquea
        (Principio II). SendGrid si está configurado, si no queda en el log."""
        asunto = f"Quiebre de alta demanda — producto {evento.product_id}"
        cuerpo = (
            f"Se registró un quiebre de stock de un producto clasificación A "
            f"(producto {evento.product_id}, tienda {evento.tienda_id})."
        )
        enviado = False
        if sendgrid_client.is_configured() and settings.sendgrid_from_email:
            enviado = sendgrid_client.enviar_correo(
                to=settings.sendgrid_from_email, subject=asunto, html=cuerpo
            )
        if not enviado:
            logger.warning("ALTA DEMANDA (sin correo): %s", cuerpo)

    # ================================================= US3: stock máximo (R9)
    async def definir_stock_maximo(self, data: StockMaximoIn) -> StockMaximoCategoria:
        existente = await self.repo.get_stock_maximo(data.product_category, data.tienda_id)
        if existente is None:
            existente = StockMaximoCategoria(
                product_category=data.product_category,
                tienda_id=data.tienda_id,
                cantidad_maxima=data.cantidad_maxima,
                empleado_id=data.empleado_id,
            )
            self.repo.agregar(existente)
        else:
            existente.cantidad_maxima = data.cantidad_maxima
            existente.empleado_id = data.empleado_id
            existente.fecha_definicion = _ahora()
        existente.capacidad_gondola = data.capacidad_gondola
        existente.stock_minimo_reorden = data.stock_minimo_reorden
        existente.dias_cobertura = data.dias_cobertura
        existente.politica_sobrestock = data.politica_sobrestock
        await self.repo.flush()
        return existente

    async def buscar_productos(self, termino: str):
        return await self.repo.buscar_productos(termino)

    async def listar_stock(
        self, params, *, tienda_id, search=None, categoria=None, estado=None
    ) -> dict:
        filas, total = await self.repo.stock_por_sku(
            tienda_id=tienda_id,
            search=search,
            categoria=categoria,
            estado=estado,
            offset=params.offset,
            limit=params.limit,
        )
        return {"items": filas, "total": total, "page": params.page, "size": params.size}

    async def resumen_stock(self, tienda_id: int) -> dict:
        return await self.repo.resumen_stock(tienda_id)

    async def solicitar_reposicion(self, data) -> dict:
        """"Reordenar" desde la pantalla de stock: deja una alerta `reposicion`
        pendiente (si no la hay) y avisa al rol de compras. El registro de
        negocio es la alerta; la notificación no lo bloquea (Principio II)."""
        producto = await self.repo.get_producto(data.product_id)
        if producto is None:
            raise NotFoundError(f"Producto {data.product_id} no existe")

        existente = await self.repo.alerta_pendiente(
            data.product_id, data.tienda_id, "reposicion"
        )
        if existente is not None:
            self._notificar_reposicion(data.product_id, data.tienda_id)
            return {"alerta_id": existente.alerta_id, "ya_existia": True, "notificado": True}

        alerta = AlertaInventario(
            tipo="reposicion",
            product_id=data.product_id,
            tienda_id=data.tienda_id,
            estado="pendiente",
            origen_calculo="rotacion_reciente",
        )
        self.repo.agregar(alerta)
        await self.repo.flush()
        self._notificar_reposicion(data.product_id, data.tienda_id)
        return {"alerta_id": alerta.alerta_id, "ya_existia": False, "notificado": True}

    def _notificar_reposicion(self, product_id: int, tienda_id: int) -> None:
        asunto = f"Solicitud de reposición — producto {product_id}"
        cuerpo = (
            f"Se solicitó reponer el producto {product_id} de la tienda {tienda_id} "
            f"(sin pedido en tránsito). Crear la orden de compra correspondiente."
        )
        enviado = False
        if sendgrid_client.is_configured() and settings.sendgrid_from_email:
            enviado = sendgrid_client.enviar_correo(
                to=settings.sendgrid_from_email, subject=asunto, html=cuerpo
            )
        if not enviado:
            logger.warning("SOLICITUD REPOSICIÓN (sin correo): %s", cuerpo)

    async def definir_ubicacion(self, data) -> dict:
        if await self.repo.get_producto(data.product_id) is None:
            raise NotFoundError(f"El producto {data.product_id} no existe")
        return await self.repo.upsert_ubicacion(
            product_id=data.product_id,
            tienda_id=data.tienda_id,
            pasillo=data.pasillo,
            gondola=data.gondola,
            nivel=data.nivel,
            empleado_id=data.empleado_id,
        )

    async def listar_stock_maximo(self, params, *, tienda_id: int, product_category=None):
        stmt = self.repo.stock_maximo_query(tienda_id=tienda_id, product_category=product_category)
        return await self.repo.paginate(
            params, stmt=stmt, order_by=StockMaximoCategoria.product_category.asc()
        )

    # ============================================ US3: verificación anaquel (R10)
    async def registrar_verificacion_anaquel(
        self, data: VerificacionAnaquelIn
    ) -> VerificacionAnaquel:
        producto = await self.repo.get_producto(data.product_id)
        if producto is None:
            raise NotFoundError(f"Producto {data.product_id} no existe")
        if producto.clasificacion_abc != "A":
            raise BusinessRuleError(
                "La verificación de anaquel sólo aplica a productos clasificación A (FR-042)"
            )

        fecha = data.fecha or date.today()
        existente = await self.repo.get_verificacion_anaquel(data.product_id, data.tienda_id, fecha)
        if existente is None:
            existente = VerificacionAnaquel(
                product_id=data.product_id,
                tienda_id=data.tienda_id,
                fecha=fecha,
                disponible=data.disponible,
                empleado_id=data.empleado_id,
            )
            self.repo.agregar(existente)
        else:
            existente.disponible = data.disponible
            existente.empleado_id = data.empleado_id
        existente.facing_asignado = data.facing_asignado
        existente.facing_real = data.facing_real
        existente.esl_ok = data.esl_ok
        existente.fifo_ok = data.fifo_ok
        existente.observaciones = data.observaciones
        await self.repo.flush()
        return existente
