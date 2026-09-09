"""ComprasService — sugerencia de compra, órdenes, pedidos especiales y el ciclo
de cuentas por pagar a proveedor (US3). Toda la regla vive aquí (Principio V).
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from decimal import Decimal

from src.core.config import settings
from src.integrations import sendgrid_client
from src.models.factura_proveedor import FacturaProveedor
from src.models.orden_compra import OrdenCompra
from src.models.orden_compra_detalle import OrdenCompraDetalle
from src.models.pago_proveedor import PagoProveedor
from src.models.proveedor import Proveedor
from src.modules.compras.repository import ComprasRepository
from src.modules.compras.schemas import (
    FacturaIn,
    OrdenIn,
    PagoIn,
    ProveedorIn,
    ProveedorPatch,
)
from src.shared.exceptions import (
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)

logger = logging.getLogger("sira.compras")


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normaliza_historial(row: dict) -> dict:
    """`cantidad_total` llega como Decimal/None desde SUM(); lo dejamos int."""
    out = dict(row)
    out["ordenes"] = int(out.get("ordenes") or 0)
    out["cantidad_total"] = int(out.get("cantidad_total") or 0)
    return out


class ComprasService:
    def __init__(self, repo: ComprasRepository) -> None:
        self.repo = repo

    # -------------------------------------------------------- proveedores
    async def crear_proveedor(self, data: ProveedorIn) -> Proveedor:
        proveedor = Proveedor(**data.model_dump(exclude_none=True))
        self.repo.agregar(proveedor)
        await self.repo.flush()
        return proveedor

    async def actualizar_proveedor(self, proveedor_id: int, data: ProveedorPatch) -> Proveedor:
        proveedor = await self.repo.get_proveedor(proveedor_id)
        if proveedor is None:
            raise NotFoundError(f"Proveedor {proveedor_id} no existe")
        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(proveedor, campo, valor)
        await self.repo.flush()
        return proveedor

    # -------------------------------------------------------- sugerencia (FR-023)
    async def generar_sugerencia_semanal(self, tienda_id: int) -> list[dict]:
        # feature 004 (FR-009/FR-010): la cantidad sugerida se basa en el pronóstico
        # vigente cuando existe; si no, en la rotación reciente de 001 (respaldo).
        from src.modules.forecasting.repository import ForecastingRepository
        from src.modules.forecasting.service import ForecastingService

        forecasting = ForecastingService(ForecastingRepository(self.repo.session))

        sugerencias: list[dict] = []
        for inv in await self.repo.productos_bajo_punto(tienda_id):
            pronostico = await forecasting.demanda_semanal_vigente(inv.product_id, tienda_id)
            if pronostico is not None:
                # Cubrir ~2 semanas de demanda proyectada.
                objetivo = round(pronostico * 2)
                origen = "modelo_pronostico"
            else:
                objetivo = inv.cantidad_minima * 2  # heurística MVP de 001
                origen = "rotacion_reciente"
            cantidad = max(1, objetivo - inv.cantidad_disponible)
            proveedor_id = await self.repo.ultimo_proveedor_de(inv.product_id, tienda_id)
            sugerencias.append(
                {
                    "product_id": inv.product_id,
                    "tienda_id": tienda_id,
                    "proveedor_id": proveedor_id,
                    "cantidad_disponible": inv.cantidad_disponible,
                    "punto_reposicion": inv.cantidad_minima,
                    "cantidad_sugerida": cantidad,
                    "origen_calculo": origen,
                }
            )

        # feature 012 (FR-002): disponibilidad del producto en las OTRAS tiendas de
        # la red, embebida en la misma respuesta (research.md Decisión 5).
        if sugerencias:
            from src.modules.traslados.repository import TrasladosRepository

            por_producto = await TrasladosRepository(self.repo.session).disponibilidad_por_producto(
                [s["product_id"] for s in sugerencias]
            )
            for s in sugerencias:
                s["disponibilidad_otras_tiendas"] = [
                    d for d in por_producto.get(s["product_id"], []) if d["tienda_id"] != tienda_id
                ]
        return sugerencias

    # -------------------------------------------------------- órdenes (FR-024)
    async def crear_orden(self, data: OrdenIn) -> OrdenCompra:
        if await self.repo.get_proveedor(data.proveedor_id) is None:
            raise NotFoundError(f"Proveedor {data.proveedor_id} no existe")

        sugerencias = await self.generar_sugerencia_semanal(data.tienda_id)
        sugerencia = {s["product_id"]: s["cantidad_sugerida"] for s in sugerencias}
        origen_por_producto = {s["product_id"]: s["origen_calculo"] for s in sugerencias}
        difiere = any(sugerencia.get(ln.product_id) != ln.cantidad for ln in data.lineas)
        if difiere and not (data.motivo_desviacion or "").strip():
            raise BusinessRuleError(
                "La orden difiere de la sugerencia del sistema: falta motivo_desviacion (FR-024)"
            )

        orden = OrdenCompra(
            proveedor_id=data.proveedor_id,
            tienda_id=data.tienda_id,
            empleado_id=data.empleado_id,
            estado="pendiente",
            tipo=data.tipo,
            motivo_desviacion=data.motivo_desviacion,
        )
        self.repo.agregar(orden)
        await self.repo.flush()
        for ln in data.lineas:
            self.repo.agregar(
                OrdenCompraDetalle(
                    orden_id=orden.orden_id,
                    product_id=ln.product_id,
                    cantidad=ln.cantidad,
                    costo_unitario=ln.costo_unitario,
                    origen_calculo=origen_por_producto.get(ln.product_id, "rotacion_reciente"),
                )
            )
        await self.repo.flush()
        return orden

    async def listar_ordenes(
        self,
        *,
        tienda_id: int | None = None,
        estado: str | None = None,
        limit: int = 50,
    ) -> list[OrdenCompra]:
        return await self.repo.listar_ordenes(tienda_id=tienda_id, estado=estado, limit=limit)

    async def aprobar_orden(self, orden_id: int, empleado_id: int) -> OrdenCompra:
        orden = await self.repo.get_orden_for_update(orden_id)
        if orden is None:
            raise NotFoundError(f"Orden {orden_id} no existe")
        if orden.estado != "pendiente":
            raise BusinessRuleError(
                f"Sólo se aprueba una orden 'pendiente' (está '{orden.estado}')"
            )
        orden.estado = "aprobada"
        orden.empleado_id = empleado_id
        await self.repo.flush()
        return orden

    async def pedido_especial(self, orden_id: int, motivo: str) -> OrdenCompra:
        """FR-029: convierte la orden en un pedido especial fuera de calendario y
        envía la solicitud al proveedor por correo. El registro de negocio no
        depende de que el correo llegue (Principio II)."""
        orden = await self.repo.get_orden_for_update(orden_id)
        if orden is None:
            raise NotFoundError(f"Orden {orden_id} no existe")
        if orden.estado not in ("pendiente", "aprobada"):
            raise BusinessRuleError(f"No se puede marcar como especial una orden '{orden.estado}'")
        orden.tipo = "especial"
        orden.motivo_desviacion = motivo
        await self.repo.flush()

        proveedor = await self.repo.get_proveedor(orden.proveedor_id)
        lineas = await self.repo.lineas_de_orden(orden_id)
        detalle = "".join(
            f"<li>Producto {ln.product_id}: {ln.cantidad} u. @ {ln.costo_unitario}</li>"
            for ln in lineas
        )
        html = (
            f"<p>Pedido especial fuera de calendario.</p>"
            f"<p><strong>Motivo:</strong> {motivo}</p><ul>{detalle}</ul>"
        )
        destino = getattr(proveedor, "contacto", None) or settings.sendgrid_from_email
        enviado = False
        if sendgrid_client.is_configured() and destino:
            enviado = sendgrid_client.enviar_correo(
                to=destino, subject=f"Pedido especial — orden {orden_id}", html=html
            )
        if not enviado:
            logger.warning("Pedido especial orden %s sin correo enviado", orden_id)
        return orden

    # ------------------------------------------------ cuentas por pagar (FR-033/34/35)
    async def registrar_factura(self, data: FacturaIn) -> FacturaProveedor:
        orden = await self.repo.get_orden_for_update(data.orden_id)
        if orden is None:
            raise NotFoundError(f"Orden {data.orden_id} no existe")
        if orden.estado != "recibida":
            raise BusinessRuleError(
                f"La factura sólo se registra contra una orden 'recibida' (está '{orden.estado}')"
            )
        if await self.repo.factura_existe(data.orden_id, data.numero_factura):
            raise ConflictError(
                f"Ya existe la factura {data.numero_factura} para la orden {data.orden_id}"
            )
        factura = FacturaProveedor(
            orden_id=data.orden_id,
            numero_factura=data.numero_factura,
            monto_total=data.monto_total,
            fecha_emision=data.fecha_emision,
            fecha_vencimiento=data.fecha_vencimiento,
            estado="pendiente",
            empleado_registra_id=data.empleado_registra_id,
        )
        self.repo.agregar(factura)
        await self.repo.flush()
        return factura

    async def registrar_pago(self, factura_id: int, data: PagoIn) -> PagoProveedor:
        # FR-034 / SC-009: control de doble persona, sin excepción por monto.
        if data.empleado_registra_id == data.empleado_autoriza_id:
            raise ForbiddenError("Quien registra el pago debe ser distinto de quien lo autoriza")

        factura = await self.repo.get_factura_for_update(factura_id)
        if factura is None:
            raise NotFoundError(f"Factura {factura_id} no existe")
        if factura.estado == "pagada":
            raise BusinessRuleError("La factura ya está pagada")
        if not await self.repo.medio_pago_existe(data.medio_pago_id):
            raise NotFoundError(f"medio_pago_id {data.medio_pago_id} no existe")

        pagado = await self.repo.pagado_de_factura(factura_id)
        if pagado + data.monto > Decimal(str(factura.monto_total)):
            raise ConflictError(
                f"El pago excede el saldo de la factura (saldo {factura.monto_total - pagado})"
            )

        pago = PagoProveedor(
            factura_id=factura_id,
            monto=data.monto,
            medio_pago_id=data.medio_pago_id,
            referencia=data.referencia,
            empleado_registra_id=data.empleado_registra_id,
            empleado_autoriza_id=data.empleado_autoriza_id,
        )
        self.repo.agregar(pago)
        await self.repo.flush()

        # FR-035: recalcular el estado en la capa de servicio (no un trigger).
        nuevo_pagado = pagado + data.monto
        if nuevo_pagado >= Decimal(str(factura.monto_total)):
            factura.estado = "pagada"
        else:
            factura.estado = "pagada_parcial"
        await self.repo.flush()
        return pago

    # --------------------------------------------------- reportes (Ronda 10)
    async def resumen_cuentas_por_pagar(self, desde: date, hasta: date) -> dict:
        total = Decimal("0.00")
        abiertas = 0
        for factura in await self.repo.facturas_abiertas_en(desde, hasta):
            pagado = await self.repo.pagado_de_factura(factura.factura_id)
            saldo = Decimal(str(factura.monto_total)) - pagado
            if saldo > 0:
                total += saldo
                abiertas += 1
        return {
            "desde": desde,
            "hasta": hasta,
            "total_por_pagar": total,
            "facturas_abiertas": abiertas,
        }

    # ---------------------------------------- historial proveedor↔producto (R11, FR-044)
    async def productos_de_proveedor(self, proveedor_id: int) -> list[dict]:
        if await self.repo.get_proveedor(proveedor_id) is None:
            raise NotFoundError(f"Proveedor {proveedor_id} no existe")
        return [
            _normaliza_historial(r) for r in await self.repo.productos_de_proveedor(proveedor_id)
        ]

    async def proveedores_de_producto(self, product_id: int) -> list[dict]:
        if await self.repo.get_producto(product_id) is None:
            raise NotFoundError(f"Producto {product_id} no existe")
        return [
            _normaliza_historial(r) for r in await self.repo.proveedores_de_producto(product_id)
        ]

    async def reporte_automatico_vs_manual(self, mes: str) -> dict:
        anio, mes_num = (int(x) for x in mes.split("-"))
        desde = date(anio, mes_num, 1)
        hasta = date(anio + 1, 1, 1) if mes_num == 12 else date(anio, mes_num + 1, 1)
        conteo = await self.repo.contar_ordenes_por_tipo(desde, hasta)
        programadas = conteo.get("programada", 0)
        especiales = conteo.get("especial", 0)
        total = programadas + especiales
        return {
            "mes": mes,
            "total": total,
            "programadas": programadas,
            "especiales": especiales,
            "pct_programadas": round(programadas / total * 100, 1) if total else 0.0,
        }
