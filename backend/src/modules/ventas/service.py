"""VentasService — toda la regla de negocio del punto de venta (Principio V/XI).

El router sólo traduce HTTP ↔ estos métodos; el frontend nunca replica esta
lógica.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal

from src.integrations import reportlab_invoice, stripe_client
from src.models.anulacion_venta import AnulacionVenta
from src.models.devolucion import Devolucion
from src.models.intento_pago_tarjeta import IntentoPagoTarjeta
from src.models.linea_venta_removida import LineaVentaRemovida
from src.models.medio_pago import MedioPago
from src.models.movimiento_inventario import MovimientoInventario
from src.models.venta import Venta
from src.models.venta_detalle import VentaDetalle
from src.modules.ventas.repository import VentasRepository
from src.modules.ventas.schemas import (
    AgregarLineaIn,
    AnularVentaIn,
    ConfirmarVentaIn,
    DescuentoManualIn,
    DevolucionIn,
    IniciarVentaIn,
    PagoTarjetaIn,
    RemoverLineaIn,
)
from src.shared import pagos
from src.shared import pricing as pricing_calc
from src.shared.exceptions import (
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from src.shared.inventario_fifo import ordenar_lotes_fifo_fefo

logger = logging.getLogger("sira.ventas")

# Nombre del medio de pago que exige un intento de tarjeta aprobado antes de confirmar.
MEDIO_PAGO_TARJETA = "Tarjeta"

# Palabras del motivo que impiden reintegrar el producto al stock vendible (FR-025).
_MOTIVOS_NO_REINTEGRO = ("dañad", "daño", "roto", "defectuos", "vencid", "mal estado", "abiert")


def _motivo_reintegra(motivo: str) -> bool:
    m = motivo.lower()
    return not any(clave in m for clave in _MOTIVOS_NO_REINTEGRO)


def _semana_iso(dt: datetime) -> int:
    return dt.isocalendar().week


def calcular_total(lineas: Iterable[VentaDetalle]) -> Decimal:
    """Total línea a línea: Σ (precio unitario × cantidad − descuento manual de la
    línea). Sin redondeos intermedios — `Decimal` conserva la precisión de 2
    decimales. `retail_disc` (feature 003) es el monto total del descuento manual
    autorizado de esa línea; 0 en el flujo base de 001."""
    total = Decimal("0")
    for linea in lineas:
        total += Decimal(str(linea.sales_value)) * linea.cantidad
        total -= Decimal(str(getattr(linea, "retail_disc", 0) or 0))
    return total.quantize(Decimal("0.01"))


class VentasService:
    def __init__(self, repo: VentasRepository) -> None:
        self.repo = repo

    # ------------------------------------------------------------------ US1
    async def iniciar_venta(self, data: IniciarVentaIn) -> Venta:
        ahora = datetime.now(UTC).replace(tzinfo=None)
        venta = Venta(
            tienda_id=data.tienda_id,
            cajero_id=data.cajero_id,
            household_id=data.household_id,
            fecha_hora=ahora,
            # feature 007 (FR-015): marca de inicio del cobro. `fecha_hora` se
            # re-sella al confirmar (research.md Decisión 6) — la diferencia es la
            # duración total del cobro.
            fecha_inicio_cobro=ahora,
            semana=_semana_iso(ahora),
            estado="en_curso",
            total=Decimal("0.00"),
        )
        self.repo.agregar(venta)
        await self.repo.flush()
        return venta

    async def _venta_en_curso(self, venta_id: int) -> Venta:
        venta = await self.repo.get_venta(venta_id)
        if venta is None:
            raise NotFoundError(f"Venta {venta_id} no existe")
        if venta.estado != "en_curso":
            raise BusinessRuleError(f"La venta {venta_id} está '{venta.estado}', no admite cambios")
        return venta

    async def agregar_linea(
        self, venta_id: int, data: AgregarLineaIn
    ) -> tuple[Venta, VentaDetalle]:
        venta = await self._venta_en_curso(venta_id)

        if data.product_id is not None:
            producto = await self.repo.get_producto(data.product_id)
        else:
            producto = await self.repo.get_producto_por_barcode(data.codigo_barras or "")
        if producto is None:
            raise NotFoundError("Producto no encontrado")
        if producto.precio_base is None:
            raise BusinessRuleError(
                f"El producto {producto.product_id} no tiene precio_base definido"
            )

        # FR-006: no exceder el stock disponible de la tienda.
        lineas = await self.repo.lineas_de(venta_id)
        disponible = await self.repo.stock_disponible(producto.product_id, venta.tienda_id)
        ya_en_venta = sum(ln.cantidad for ln in lineas if ln.product_id == producto.product_id)
        if ya_en_venta + data.cantidad > disponible:
            raise ConflictError(
                f"Stock insuficiente para el producto {producto.product_id}: "
                f"disponible {disponible}, solicitado {ya_en_venta + data.cantidad}"
            )

        # "Agregar producto" acumula sobre la línea existente del mismo producto
        # (una fila por SKU en el ticket), salvo que ya tenga descuentos aplicados.
        linea = next(
            (
                ln
                for ln in lineas
                if ln.product_id == producto.product_id
                and not (ln.retail_disc or ln.coupon_disc or ln.coupon_match_disc)
            ),
            None,
        )
        if linea is not None:
            linea.cantidad += data.cantidad
        else:
            linea = VentaDetalle(
                venta_id=venta_id,
                product_id=producto.product_id,
                cantidad=data.cantidad,
                sales_value=producto.precio_base,
            )
            self.repo.agregar(linea)
        await self.repo.flush()

        venta.total = calcular_total(await self.repo.lineas_de(venta_id))
        await self.repo.flush()
        return venta, linea

    async def remover_linea(self, venta_id: int, linea_id: int, data: RemoverLineaIn) -> Venta:
        venta = await self._venta_en_curso(venta_id)
        linea = await self.repo.get_linea(venta_id, linea_id)
        if linea is None:
            raise NotFoundError(f"La línea {linea_id} no pertenece a la venta {venta_id}")

        # FR-027 / SC-007: control de doble persona, sin excepciones.
        if data.autoriza_empleado_id == venta.cajero_id:
            raise ForbiddenError(
                "Quien autoriza la remoción debe ser distinto del cajero de la venta"
            )

        self.repo.agregar(
            LineaVentaRemovida(
                venta_id=venta_id,
                product_id=linea.product_id,
                cantidad=linea.cantidad,
                cajero_id=venta.cajero_id,
                autoriza_empleado_id=data.autoriza_empleado_id,
                motivo=data.motivo,
            )
        )
        await self.repo.delete(linea)

        venta.total = calcular_total(await self.repo.lineas_de(venta_id))
        await self.repo.flush()
        return venta

    # ------------------------------------------------------- feature 003
    @staticmethod
    def _precio_unitario_aplicado(linea: VentaDetalle) -> Decimal:
        """Precio unitario ya descontado, después de TODOS los descuentos de la
        línea (Edge Case de `spec.md`: descuento manual de 003 + cupón de 002):
        `sales_value - (retail_disc + coupon_disc + coupon_match_disc) / cantidad`.
        Los tres montos son totales de la línea; hoy sólo `retail_disc` recibe
        valor en el flujo, los otros dos quedan preparados para 002."""
        cantidad = linea.cantidad or 1
        descuento_total = (
            Decimal(str(linea.retail_disc or 0))
            + Decimal(str(linea.coupon_disc or 0))
            + Decimal(str(linea.coupon_match_disc or 0))
        )
        return Decimal(str(linea.sales_value)) - (descuento_total / cantidad)

    async def _calcular_margen_real_lineas(self, lineas: list[VentaDetalle]) -> None:
        """FR-002: margen real de TODA línea confirmada, con el precio ya
        descontado y el costo vigente del producto. Valor congelado (Principio II)."""
        for linea in lineas:
            producto = await self.repo.get_producto(linea.product_id)
            costo = producto.costo if producto is not None else None
            linea.margen_real = pricing_calc.margen_real_pct(
                self._precio_unitario_aplicado(linea), costo
            )
        await self.repo.flush()

    async def _margen_objetivo_efectivo(self, product_id: int) -> Decimal:
        from src.modules.pricing.repository import PricingRepository
        from src.modules.pricing.service import PricingService

        svc = PricingService(PricingRepository(self.repo.session))
        data = await svc.margen_objetivo_efectivo(product_id)
        return data["margen_objetivo_efectivo"]

    async def aplicar_descuento_manual(
        self, venta_id: int, linea_id: int, data: DescuentoManualIn
    ) -> tuple[Venta, VentaDetalle]:
        """FR-009/FR-010 — control detectivo + preventivo del descuento manual.

        Autorización obligatoria de un empleado distinto con rol
        `Encargado_Tienda` o superior (research.md §4), sin excepción por monto.
        Si el margen real resultante cae bajo el margen objetivo efectivo del
        producto, la línea se marca `margen_bajo_minimo` sin bloquear la venta.
        """
        venta = await self._venta_en_curso(venta_id)
        linea = await self.repo.get_linea(venta_id, linea_id)
        if linea is None:
            raise NotFoundError(f"La línea {linea_id} no pertenece a la venta {venta_id}")

        if data.empleado_aplica_id == data.empleado_autoriza_id:
            raise ForbiddenError("Quien autoriza el descuento debe ser distinto de quien lo aplica")
        rol_autoriza = await self.repo.rol_de_empleado(data.empleado_autoriza_id)
        if not pricing_calc.rol_autoriza_descuento(rol_autoriza):
            raise ForbiddenError(
                "Sólo un Encargado_Tienda (o superior) puede autorizar un descuento manual"
            )

        cantidad = linea.cantidad or 1
        bruto_linea = Decimal(str(linea.sales_value)) * cantidad
        if data.tipo == "porcentaje":
            descuento = (bruto_linea * data.valor / 100).quantize(Decimal("0.01"))
        else:
            descuento = Decimal(str(data.valor)).quantize(Decimal("0.01"))
        descuento = min(descuento, bruto_linea)  # nunca deja el precio negativo

        linea.retail_disc = descuento
        linea.motivo_descuento = data.motivo
        linea.empleado_aplica_id = data.empleado_aplica_id
        linea.empleado_autoriza_id = data.empleado_autoriza_id

        producto = await self.repo.get_producto(linea.product_id)
        costo = producto.costo if producto is not None else None
        linea.margen_real = pricing_calc.margen_real_pct(
            self._precio_unitario_aplicado(linea), costo
        )
        objetivo = await self._margen_objetivo_efectivo(linea.product_id)
        linea.margen_bajo_minimo = linea.margen_real is not None and linea.margen_real < objetivo

        venta.total = calcular_total(await self.repo.lineas_de(venta_id))
        await self.repo.flush()
        return venta, linea

    async def procesar_pago_tarjeta(self, venta_id: int, data: PagoTarjetaIn) -> IntentoPagoTarjeta:
        await self._venta_en_curso(venta_id)

        resultado = await stripe_client.crear_intento_pago(data.monto, escenario=data.escenario)
        intento = IntentoPagoTarjeta(
            venta_id=venta_id,
            resultado=resultado.resultado,
            referencia_pasarela=resultado.referencia_pasarela,
            monto=data.monto,
        )
        self.repo.agregar(intento)
        await self.repo.flush()
        return intento

    async def confirmar_venta(self, venta_id: int, data: ConfirmarVentaIn) -> Venta:
        venta = await self._venta_en_curso(venta_id)
        lineas = await self.repo.lineas_de(venta_id)
        if not lineas:
            raise BusinessRuleError("No se puede confirmar una venta sin líneas")

        medio = await self.repo.get_medio_pago(data.medio_pago_id)
        if medio is None:
            raise NotFoundError(f"medio_pago_id {data.medio_pago_id} no existe")
        if medio.nombre == MEDIO_PAGO_TARJETA and not await self.repo.tiene_intento_aprobado(
            venta_id
        ):
            raise BusinessRuleError("El cobro con tarjeta requiere un intento de pago aprobado")

        await self._descontar_inventario_fifo(venta, lineas)
        await self._calcular_margen_real_lineas(lineas)

        venta.total = calcular_total(lineas)
        venta.estado = "confirmada"
        # feature 007 (FR-015): `fecha_hora` es el momento de CONFIRMACIÓN (el
        # dataset sembrado ya la usa así); `fecha_inicio_cobro` conserva el inicio.
        # Sólo se re-sella para ventas registradas en vivo por el flujo (siempre
        # traen `fecha_inicio_cobro`).
        if venta.fecha_inicio_cobro is not None:
            ahora = datetime.now(UTC).replace(tzinfo=None)
            venta.fecha_hora = ahora
            venta.semana = _semana_iso(ahora)
        venta.medio_pago_id = data.medio_pago_id
        venta.tipo_comprobante = data.tipo_comprobante
        if data.tipo_comprobante == "factura":
            venta.identificacion_comprador = (data.identificacion_comprador or "").strip()
            venta.razon_social_comprador = (
                data.razon_social_comprador or ""
            ).strip() or "SIN RAZÓN SOCIAL"
        await self.repo.flush()

        # feature 005 (FR-006): si la venta es de un cliente identificado y contiene
        # el antecedente de una regla de afinidad vigente sin el consecuente, dispara
        # el cupón de afinidad. Best-effort — un fallo no revierte la venta (Principio II).
        if venta.household_id is not None:
            try:
                from src.modules.promociones.repository import PromocionesRepository
                from src.modules.promociones.service import PromocionesService

                await PromocionesService(
                    PromocionesRepository(self.repo.session)
                ).evaluar_venta_para_afinidad(venta_id)
            except Exception:  # noqa: BLE001
                logger.exception("No se pudo evaluar la venta %s para cupón de afinidad", venta_id)

        venta.comprobante_objeto = await self._emitir_comprobante(venta, lineas)
        await self.repo.flush()
        return venta

    async def _descontar_inventario_fifo(self, venta: Venta, lineas: list[VentaDetalle]) -> None:
        """FR-005: descuenta por lote en orden FIFO/FEFO, bajo `FOR UPDATE`."""
        for linea in lineas:
            inv = await self.repo.get_inventario_for_update(linea.product_id, venta.tienda_id)
            if inv is None or inv.cantidad_disponible < linea.cantidad:
                raise ConflictError(
                    f"Stock insuficiente al confirmar (producto {linea.product_id})"
                )

            restante = linea.cantidad
            candidatos = ordenar_lotes_fifo_fefo(
                await self.repo.lotes_para_consumo(linea.product_id, venta.tienda_id)
            )
            for lote in candidatos:
                if restante == 0:
                    break
                toma = min(restante, lote.cantidad_disponible)
                lote.cantidad_disponible -= toma
                restante -= toma
                self.repo.agregar(
                    MovimientoInventario(
                        product_id=linea.product_id,
                        tienda_id=venta.tienda_id,
                        tipo="salida",
                        cantidad=toma,
                        referencia_tabla="venta_detalle",
                        referencia_id=linea.venta_detalle_id,
                        lote_id=lote.lote_id,
                    )
                )

            if restante > 0:
                raise BusinessRuleError(
                    f"Los lotes del producto {linea.product_id} no cubren "
                    f"{linea.cantidad} unidades (faltan {restante})"
                )
            inv.cantidad_disponible -= linea.cantidad

        await self.repo.flush()

    async def _emitir_comprobante(self, venta: Venta, lineas: list[VentaDetalle]) -> str | None:
        try:
            items = []
            for ln in lineas:
                prod = await self.repo.get_producto(ln.product_id)
                desc = (
                    (prod.product_type or prod.product_category or f"Producto {ln.product_id}")
                    if prod
                    else f"Producto {ln.product_id}"
                )
                items.append(
                    reportlab_invoice.LineaComprobante(
                        descripcion=desc,
                        cantidad=ln.cantidad,
                        precio_unitario=Decimal(str(ln.sales_value)),
                    )
                )
            datos = reportlab_invoice.DatosComprobante(
                venta_id=venta.venta_id,
                tienda=f"Tienda {venta.tienda_id}",
                fecha_hora=venta.fecha_hora,
                tipo_comprobante=venta.tipo_comprobante,
                identificacion_comprador=venta.identificacion_comprador,
                razon_social_comprador=venta.razon_social_comprador,
                lineas=items,
                total=Decimal(str(venta.total)),
            )
            return reportlab_invoice.generar_y_subir_comprobante(datos)
        except Exception:  # noqa: BLE001
            # Principio II: la venta ya es un registro real; un fallo del servicio
            # de archivos no la revierte. El comprobante se puede regenerar luego.
            logger.exception(
                "No se pudo emitir/subir el comprobante de la venta %s", venta.venta_id
            )
            return None

    async def anular_venta(self, venta_id: int, data: AnularVentaIn) -> Venta:
        venta = await self.repo.get_venta(venta_id)
        if venta is None:
            raise NotFoundError(f"Venta {venta_id} no existe")
        if venta.estado != "confirmada":
            raise BusinessRuleError(f"Sólo se anula una venta 'confirmada' (está '{venta.estado}')")
        # FR-007: "sólo antes del cierre de caja de esa jornada". Sin el módulo de
        # caja (feature 006), se aproxima con el mismo día calendario.
        if venta.fecha_hora.date() != datetime.now(UTC).date():
            raise BusinessRuleError("La venta sólo puede anularse durante la misma jornada")

        for mov in await self.repo.movimientos_salida_de(venta_id):
            if mov.lote_id is not None:
                lote = await self.repo.get_lote_for_update(mov.lote_id)
                if lote is not None:
                    lote.cantidad_disponible += mov.cantidad
            inv = await self.repo.get_inventario_for_update(mov.product_id, mov.tienda_id)
            if inv is not None:
                inv.cantidad_disponible += mov.cantidad
            self.repo.agregar(
                MovimientoInventario(
                    product_id=mov.product_id,
                    tienda_id=mov.tienda_id,
                    tipo="entrada",
                    cantidad=mov.cantidad,
                    referencia_tabla="anulaciones_venta",
                    referencia_id=venta_id,
                    lote_id=mov.lote_id,
                )
            )

        venta.estado = "anulada"
        self.repo.agregar(
            AnulacionVenta(venta_id=venta_id, empleado_id=data.empleado_id, motivo=data.motivo)
        )
        await self.repo.flush()
        return venta

    # ------------------------------------------------------------------ US5
    async def registrar_devolucion(
        self, venta_id: int, data: DevolucionIn, empleado_id: int
    ) -> Devolucion:
        venta = await self.repo.get_venta(venta_id)
        if venta is None:
            raise NotFoundError(f"Venta {venta_id} no existe")
        if venta.estado != "confirmada":
            raise BusinessRuleError(
                f"Sólo se devuelve sobre una venta 'confirmada' (está '{venta.estado}')"
            )

        lineas = await self.repo.lineas_de(venta_id)
        vendida = sum(ln.cantidad for ln in lineas if ln.product_id == data.product_id)
        if vendida == 0:
            raise BusinessRuleError(f"El producto {data.product_id} no está en la venta {venta_id}")
        ya_devuelto = await self.repo.cantidad_devuelta(venta_id, data.product_id)
        if ya_devuelto + data.cantidad > vendida:
            raise ConflictError(
                f"La devolución excede lo vendido (vendido {vendida}, ya devuelto {ya_devuelto})"
            )

        reintegra = (
            data.reintegra_inventario
            if data.reintegra_inventario is not None
            else _motivo_reintegra(data.motivo)
        )

        devolucion = Devolucion(
            venta_id=venta_id,
            product_id=data.product_id,
            cantidad=data.cantidad,
            motivo=data.motivo,
            empleado_id=empleado_id,
            reintegra_inventario=reintegra,
        )
        self.repo.agregar(devolucion)
        await self.repo.flush()

        # FR-025/FR-026: el stock vuelve sólo si el motivo lo justifica; el
        # movimiento anota el lote de origen de la venta para la trazabilidad.
        if reintegra:
            inv = await self.repo.get_inventario_for_update(data.product_id, venta.tienda_id)
            if inv is not None:
                inv.cantidad_disponible += data.cantidad
            lote_origen = next(
                (
                    m.lote_id
                    for m in await self.repo.movimientos_salida_de(venta_id)
                    if m.product_id == data.product_id and m.lote_id is not None
                ),
                None,
            )
            if lote_origen is not None:
                lote = await self.repo.get_lote_for_update(lote_origen)
                if lote is not None:
                    lote.cantidad_disponible += data.cantidad
            self.repo.agregar(
                MovimientoInventario(
                    product_id=data.product_id,
                    tienda_id=venta.tienda_id,
                    tipo="entrada",
                    cantidad=data.cantidad,
                    referencia_tabla="devoluciones",
                    referencia_id=devolucion.devolucion_id,
                    lote_id=lote_origen,
                )
            )
            await self.repo.flush()

        return devolucion

    # ------------------------------------------------------- feature 007
    async def dar_alta_medio_pago(self, nombre: str, empleado_id: int) -> MedioPago:
        """FR-005 — alta de un medio de pago con constancia de aprobación."""
        nombre = nombre.strip()
        if await self.repo.get_medio_pago_por_nombre(nombre) is not None:
            raise ConflictError(f"Ya existe un medio de pago '{nombre}'")
        ahora = datetime.now(UTC).replace(tzinfo=None)
        return await self.repo.crear_medio_pago(
            MedioPago(
                nombre=nombre,
                aprobado=True,
                aprobado_por=empleado_id,
                fecha_aprobacion=ahora,
            )
        )

    async def dar_baja_medio_pago(self, medio_pago_id: int) -> MedioPago:
        """FR-006 — baja sin borrar la fila ni desasociar ninguna venta registrada."""
        medio = await self.repo.get_medio_pago(medio_pago_id)
        if medio is None:
            raise NotFoundError(f"medio_pago_id {medio_pago_id} no existe")
        if not medio.aprobado or medio.fecha_baja is not None:
            raise ConflictError(f"El medio de pago {medio_pago_id} ya está dado de baja")
        medio.aprobado = False
        medio.fecha_baja = datetime.now(UTC).replace(tzinfo=None)
        await self.repo.flush()
        return medio

    async def listar_medios_pago(self, aprobado: bool | None = None) -> list[MedioPago]:
        return await self.repo.listar_medios_pago(aprobado)

    async def medios_pago_disponibles(self) -> list[MedioPago]:
        """FR-007 — sólo los aprobados y no dados de baja."""
        return await self.repo.medios_pago_disponibles()

    async def datafono_disponible_de_caja(self, caja_id: int) -> dict:
        """FR-004 — consulta rápida de solo lectura del estado del datáfono de la
        caja (dato de `modules/caja/`), usada por el flujo de cobro para advertir
        antes de intentar con tarjeta. Nunca bloquea otro medio de pago."""
        estados = await self.repo.datafonos_de_caja(caja_id)
        if not estados:
            return {"disponible": False, "estado": None}
        if "activo" in estados:
            return {"disponible": True, "estado": "activo"}
        # ninguno operativo: reporta el estado del primero como referencia
        return {"disponible": False, "estado": estados[0]}

    async def listar_cajas(self, tienda_id: int | None = None) -> list[dict]:
        """FR-016 — cajas para el selector de la revisión semanal de tiempo de cobro."""
        return await self.repo.listar_cajas(tienda_id)

    async def catalogo_pos(
        self,
        *,
        tienda_id: int,
        search: str | None,
        categoria: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        """Grid de productos del POS (registro rápido) — productos con precio y
        stock en la tienda."""
        return await self.repo.catalogo_pos(
            tienda_id=tienda_id,
            search=search,
            categoria=categoria,
            offset=offset,
            limit=limit,
        )

    async def categorias_pos(self, tienda_id: int) -> list[str]:
        return await self.repo.categorias_con_stock(tienda_id)

    async def tiempo_cobro_semanal(self, caja_id: int, semana: int, anio: int | None) -> dict:
        """FR-016/FR-018 — tiempo promedio de cobro de una caja en una semana,
        excluyendo ventas anuladas y sin `fecha_inicio_cobro`."""
        cajeros = await self.repo.cajeros_de_caja(caja_id)
        ventas = (
            await self.repo.ventas_tiempo_cobro(cajero_ids=cajeros, semana=semana, anio=anio)
            if cajeros
            else []
        )
        promedio, consideradas = pagos.promedio_duracion_cobro(ventas)
        return {
            "caja_id": caja_id,
            "semana": semana,
            "duracion_promedio_segundos": promedio,
            "cantidad_ventas_consideradas": consideradas,
        }

    async def tiempo_cobro_mensual(self, mes: int, anio: int) -> list[dict]:
        """FR-017 — tiempo promedio de cobro por tienda a nivel de red, para un mes."""
        ventas = await self.repo.ventas_tiempo_cobro_mes(mes, anio)
        por_tienda: dict[int, list] = {}
        for v in ventas:
            por_tienda.setdefault(v["tienda_id"], []).append(v)
        salida = []
        for tienda_id, filas in sorted(por_tienda.items()):
            promedio, consideradas = pagos.promedio_duracion_cobro(filas)
            salida.append(
                {
                    "tienda_id": tienda_id,
                    "duracion_promedio_segundos": promedio,
                    "cantidad_ventas_consideradas": consideradas,
                }
            )
        return salida
