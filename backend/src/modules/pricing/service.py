"""PricingService — regla de negocio de precios, márgenes y competencia (feature 003).

Principio V/XI: el router sólo traduce HTTP ↔ estos métodos; el frontend nunca
replica esta lógica. Los cálculos críticos (Principio X) viven en `src/shared/pricing.py`.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from src.models.competidor import Competidor
from src.models.configuracion_pricing import (
    CLAVE_MARGEN_MINIMO_GLOBAL,
    CLAVE_TOLERANCIA_AJUSTE,
    CLAVE_UMBRAL_COMPETENCIA,
)
from src.models.margen_objetivo import MargenObjetivo
from src.models.precio_competencia import PrecioCompetencia
from src.models.propuesta_ajuste_precio import PropuestaAjustePrecio
from src.modules.pricing.repository import PricingRepository
from src.modules.pricing.schemas import CompetidorIn, PrecioCompetenciaIn
from src.shared import pricing as calc
from src.shared.exceptions import BusinessRuleError, ConflictError, NotFoundError
from src.shared.pagination import Page, PageParams

logger = logging.getLogger("sira.pricing")

VENTANA_DESVIACION_DIAS = 30
_DEFAULT_MARGEN_MINIMO = Decimal("5.0")
_DEFAULT_TOLERANCIA = Decimal("2.0")
_DEFAULT_UMBRAL_COMPETENCIA = Decimal("5.0")


def _hoy() -> date:
    return datetime.now(UTC).date()


class PricingService:
    def __init__(self, repo: PricingRepository) -> None:
        self.repo = repo

    # ==================================================== márgenes objetivo
    async def listar_margenes(self) -> list[MargenObjetivo]:
        return await self.repo.listar_margenes()

    async def definir_margen_objetivo(
        self, product_category: str, *, margen_objetivo_pct=None, factor_sensibilidad=None
    ) -> MargenObjetivo:
        """FR-001 (margen objetivo por categoría) + FR-004 (factor de sensibilidad)."""
        margen = await self.repo.get_margen(product_category)
        if margen is None:
            if margen_objetivo_pct is None:
                raise BusinessRuleError("Una categoría nueva requiere `margen_objetivo_pct`")
            margen = MargenObjetivo(
                product_category=product_category,
                margen_objetivo_pct=margen_objetivo_pct,
                factor_sensibilidad=factor_sensibilidad,
            )
            self.repo.agregar(margen)
        else:
            if margen_objetivo_pct is not None:
                margen.margen_objetivo_pct = margen_objetivo_pct
            if factor_sensibilidad is not None:
                margen.factor_sensibilidad = factor_sensibilidad
        await self.repo.flush()
        await self.repo.refrescar(margen)
        return margen

    # ============================================ margen objetivo efectivo (T022)
    async def margen_objetivo_efectivo(self, product_id: int) -> dict:
        """FR-007 — función compartida (la usan US2, US3 y US5). Valor calculado,
        nunca persistido (`data-model.md` entidad 2)."""
        producto = await self.repo.get_producto(product_id)
        if producto is None:
            raise NotFoundError(f"Producto {product_id} no existe")

        margen_cat = None
        if producto.product_category is not None:
            fila = await self.repo.get_margen(producto.product_category)
            margen_cat = fila.margen_objetivo_pct if fila is not None else None

        piso = await self.repo.valor_config(CLAVE_MARGEN_MINIMO_GLOBAL, _DEFAULT_MARGEN_MINIMO)
        efectivo, modificador, piso_aplicado = calc.margen_objetivo_efectivo(
            margen_cat, es_ancla=producto.es_ancla, margen_minimo_global=piso
        )
        return {
            "product_id": product_id,
            "product_category": producto.product_category,
            "es_ancla": producto.es_ancla,
            "margen_objetivo_categoria": (
                Decimal(str(margen_cat)) if margen_cat is not None else None
            ),
            "modificador_pp": modificador,
            "margen_objetivo_efectivo": efectivo,
            "margen_minimo_global_aplicado": piso_aplicado,
        }

    # =================================================== propuestas de ajuste
    async def listar_propuestas(
        self, params: PageParams, *, estado=None, product_category=None
    ) -> Page[PropuestaAjustePrecio]:
        stmt = self.repo.propuestas_query(estado=estado, product_category=product_category)
        return await self.repo.paginate(
            params, stmt=stmt, order_by=PropuestaAjustePrecio.fecha_generada.desc()
        )

    async def get_propuesta(self, propuesta_id: int) -> PropuestaAjustePrecio:
        propuesta = await self.repo.get_propuesta(propuesta_id)
        if propuesta is None:
            raise NotFoundError(f"Propuesta {propuesta_id} no existe")
        return propuesta

    async def aprobar_propuesta(self, propuesta_id: int, empleado_id: int) -> PropuestaAjustePrecio:
        """FR-006 / SC-002 — la única vía por la que `productos.precio_base` cambia
        por esta feature. 409 si la propuesta ya no está `pendiente`."""
        propuesta = await self.get_propuesta(propuesta_id)
        if propuesta.estado != "pendiente":
            raise ConflictError(f"La propuesta {propuesta_id} ya está '{propuesta.estado}'")
        await self.repo.publicar_precio(
            propuesta.product_id, Decimal(str(propuesta.precio_propuesto)), _hoy()
        )
        propuesta.estado = "aprobada"
        propuesta.fecha_resolucion = datetime.now(UTC).replace(tzinfo=None)
        propuesta.aprobado_por = empleado_id
        await self.repo.flush()
        return propuesta

    async def rechazar_propuesta(
        self, propuesta_id: int, empleado_id: int, motivo: str | None = None
    ) -> PropuestaAjustePrecio:
        """FR-005 — no cambia nada más; no se reintenta (el siguiente job genera
        una propuesta nueva si la desviación persiste)."""
        propuesta = await self.get_propuesta(propuesta_id)
        if propuesta.estado != "pendiente":
            raise ConflictError(f"La propuesta {propuesta_id} ya está '{propuesta.estado}'")
        propuesta.estado = "rechazada"
        propuesta.fecha_resolucion = datetime.now(UTC).replace(tzinfo=None)
        propuesta.aprobado_por = empleado_id
        if motivo:
            logger.info("Propuesta %s rechazada: %s", propuesta_id, motivo)
        await self.repo.flush()
        return propuesta

    async def generar_propuestas_ajuste(self, hoy: date | None = None) -> dict:
        """Job semanal (research.md §2/§6, FR-005). Para cada categoría con
        `factor_sensibilidad` activo: desviación = margen real 30d − margen
        objetivo; si `|desviación|` supera la tolerancia, una propuesta por
        producto activo (sin duplicar una ya pendiente)."""
        hoy = hoy or _hoy()
        desde = hoy - timedelta(days=VENTANA_DESVIACION_DIAS)
        tolerancia = await self.repo.valor_config(CLAVE_TOLERANCIA_AJUSTE, _DEFAULT_TOLERANCIA)

        categorias_evaluadas = propuestas_creadas = 0
        for margen in await self.repo.margenes_con_regla():
            categorias_evaluadas += 1
            agregado = await self.repo.agregado_margen_por_categoria(
                desde, hoy, margen.product_category
            )
            if not agregado:
                continue
            _, _, ingreso, costo = agregado[0]
            if ingreso <= 0:
                continue
            margen_real_cat = (ingreso - costo) / ingreso * 100
            desviacion_pp = margen_real_cat - Decimal(str(margen.margen_objetivo_pct))
            if abs(desviacion_pp) < tolerancia:
                continue

            factor = Decimal(str(margen.factor_sensibilidad))
            for producto in await self.repo.productos_de_categoria(margen.product_category):
                if producto.precio_base is None:
                    continue
                if await self.repo.propuesta_pendiente_de(producto.product_id) is not None:
                    continue
                nuevo = calc.precio_propuesto(
                    producto.precio_base, factor, desviacion_pp, producto.costo
                )
                if nuevo == Decimal(str(producto.precio_base)):
                    continue
                margen_esperado = calc.margen_real_pct(nuevo, producto.costo) or Decimal("0")
                self.repo.agregar(
                    PropuestaAjustePrecio(
                        product_id=producto.product_id,
                        precio_actual=producto.precio_base,
                        precio_propuesto=nuevo,
                        margen_esperado_pct=margen_esperado,
                        estado="pendiente",
                    )
                )
                propuestas_creadas += 1
        await self.repo.flush()
        return {
            "categorias_evaluadas": categorias_evaluadas,
            "propuestas_creadas": propuestas_creadas,
        }

    # =================================================== margen bajo (US3)
    async def listar_margen_bajo(
        self, params: PageParams, *, tienda_id=None, revisado=None
    ) -> dict:
        total, filas = await self.repo.margen_bajo_pagina(
            tienda_id=tienda_id, revisado=revisado, offset=params.offset, limit=params.limit
        )
        items = []
        for linea, venta_id, t_id, fecha_hora, accion in filas:
            cantidad = linea.cantidad or 1
            retail_disc = Decimal(str(linea.retail_disc or 0))
            precio_aplicado = Decimal(str(linea.sales_value)) - (retail_disc / cantidad)
            items.append(
                {
                    "venta_detalle_id": linea.venta_detalle_id,
                    "venta_id": venta_id,
                    "tienda_id": t_id,
                    "product_id": linea.product_id,
                    "cantidad": cantidad,
                    "precio_aplicado": precio_aplicado.quantize(Decimal("0.01")),
                    "margen_real": (
                        Decimal(str(linea.margen_real)) if linea.margen_real is not None else None
                    ),
                    "fecha_venta": fecha_hora,
                    "motivo_descuento": linea.motivo_descuento,
                    "revisado": accion is not None,
                    "accion_correctiva": accion,
                }
            )
        return {"items": items, "total": total, "page": params.page, "size": params.size}

    async def registrar_revision(
        self, venta_detalle_id: int, empleado_id: int, accion_correctiva: str
    ) -> None:
        """FR-012 — crea o actualiza (`UPDATE`, nunca fila nueva) la acción
        correctiva. 422 si la línea no está marcada como margen bajo."""
        linea = await self.repo.get_linea(venta_detalle_id)
        if linea is None:
            raise NotFoundError(f"Línea {venta_detalle_id} no existe")
        if not linea.margen_bajo_minimo:
            raise BusinessRuleError(
                f"La línea {venta_detalle_id} no está marcada como margen bajo mínimo"
            )
        await self.repo.upsert_revision(venta_detalle_id, empleado_id, accion_correctiva)
        await self.repo.flush()

    # =================================================== reporte de margen
    async def reporte_margen(
        self, desde: date, hasta: date, product_category: str | None = None
    ) -> dict:
        """FR-003 / FR-013 — margen real acumulado por categoría vs. margen objetivo
        vigente, en el rango. El corte mensual de FR-013 es este mismo método."""
        margenes = {m.product_category: m for m in await self.repo.listar_margenes()}
        agregado = await self.repo.agregado_margen_por_categoria(desde, hasta, product_category)
        filas = []
        for categoria, unidades, ingreso, costo in agregado:
            margen_real = (
                ((ingreso - costo) / ingreso * 100).quantize(Decimal("0.01"))
                if ingreso > 0
                else None
            )
            objetivo = margenes.get(categoria)
            filas.append(
                {
                    "product_category": categoria,
                    "margen_objetivo_pct": (
                        Decimal(str(objetivo.margen_objetivo_pct)) if objetivo else None
                    ),
                    "margen_real_pct": margen_real,
                    "unidades_vendidas": unidades,
                    "ingreso_total": ingreso.quantize(Decimal("0.01")),
                    "costo_total": costo.quantize(Decimal("0.01")),
                }
            )
        return {"fecha_desde": desde, "fecha_hasta": hasta, "filas": filas}

    # =================================================== competencia (US5)
    async def listar_competidores(self, *, tipo=None, ciudad=None) -> list[Competidor]:
        return await self.repo.listar_competidores(tipo=tipo, ciudad=ciudad)

    async def registrar_competidor(self, data: CompetidorIn) -> Competidor:
        competidor = Competidor(nombre=data.nombre, tipo=data.tipo, ciudad=data.ciudad)
        self.repo.agregar(competidor)
        await self.repo.flush()
        await self.repo.refrescar(competidor)
        return competidor

    async def registrar_precio_competencia_manual(
        self, product_id: int, data: PrecioCompetenciaIn, empleado_id: int
    ) -> PrecioCompetencia:
        """FR-014 — siempre `fuente_captura = 'manual'` (fijado por el servidor,
        nunca del body) y `registrado_por` = el usuario autenticado."""
        if await self.repo.get_producto(product_id) is None:
            raise NotFoundError(f"Producto {product_id} no existe")
        if await self.repo.get_competidor(data.competidor_id) is None:
            raise NotFoundError(f"Competidor {data.competidor_id} no existe")
        fila = PrecioCompetencia(
            product_id=product_id,
            competidor_id=data.competidor_id,
            tienda_id=data.tienda_id,
            precio=data.precio,
            fecha_captura=data.fecha_captura or _hoy(),
            es_promocional=data.es_promocional,
            fuente_captura="manual",
            registrado_por=empleado_id,
        )
        return await self.repo.agregar_precio_competencia(fila)

    async def precios_competencia_de(self, product_id: int) -> list[PrecioCompetencia]:
        if await self.repo.get_producto(product_id) is None:
            raise NotFoundError(f"Producto {product_id} no existe")
        return await self.repo.precios_competencia_de(product_id)

    async def alertas_competencia(self, umbral: Decimal | None = None) -> list[dict]:
        """FR-015 / FR-016 — productos cuya desviación entre `precio_base` y su
        `precio_competencia` más reciente (cualquier fuente) supera el umbral. Un
        producto sin filas no aparece (Edge Case de `spec.md`)."""
        if umbral is None:
            umbral = await self.repo.valor_config(
                CLAVE_UMBRAL_COMPETENCIA, _DEFAULT_UMBRAL_COMPETENCIA
            )
        alertas = []
        for (
            product_id,
            categoria,
            precio_base,
            precio_comp,
            fuente,
            fecha,
        ) in await self.repo.precio_competencia_mas_reciente_por_producto():
            desviacion = calc.desviacion_competencia_pct(precio_base, precio_comp)
            if desviacion is None or desviacion <= umbral:
                continue
            alertas.append(
                {
                    "product_id": product_id,
                    "product_category": categoria,
                    "precio_base": precio_base,
                    "precio_competencia": precio_comp,
                    "fuente_captura": fuente,
                    "fecha_captura": fecha,
                    "desviacion_pct": desviacion,
                }
            )
        return alertas

    # =================================================== configuración
    async def listar_configuracion(self):
        return await self.repo.listar_configuracion()

    async def actualizar_configuracion(self, clave: str, valor: Decimal):
        fila = await self.repo.get_config(clave)
        if fila is None:
            raise NotFoundError(f"Clave de configuración '{clave}' no existe")
        fila.valor = valor
        await self.repo.flush()
        return fila

    async def capturar_open_prices(self, product_id: int) -> PrecioCompetencia | None:
        """Best-effort (research.md §5): consulta Open Prices por el código de
        barras real del producto e inserta una fila `fuente_captura = 'open_prices'`
        (`competidor_id = NULL`, `registrado_por = NULL`) si hay dato. Nunca lanza."""
        from src.integrations import open_prices_client

        producto = await self.repo.get_producto(product_id)
        if producto is None or not producto.codigo_barras:
            return None
        precio = await open_prices_client.ultimo_precio_por_barcode(producto.codigo_barras)
        if precio is None:
            return None
        fila = PrecioCompetencia(
            product_id=product_id,
            competidor_id=None,
            tienda_id=None,
            precio=Decimal(str(precio)),
            fecha_captura=_hoy(),
            es_promocional=False,
            fuente_captura="open_prices",
            registrado_por=None,
        )
        return await self.repo.agregar_precio_competencia(fila)

    # --------------------------------------------- jobs periódicos
    async def refrescar_y_calcular_alertas_competencia(self) -> dict:
        """Job semanal de competencia (research.md §5/§6): refresca Open Prices
        (best-effort) para los productos en vivo con barcode real y recalcula todas
        las alertas de desviación."""
        refrescados = 0
        for producto in await self.repo.productos_en_vivo_con_barcode():
            if await self.capturar_open_prices(producto.product_id) is not None:
                refrescados += 1
        await self.repo.flush()
        alertas = await self.alertas_competencia()
        return {"open_prices_refrescados": refrescados, "alertas_competencia": len(alertas)}
