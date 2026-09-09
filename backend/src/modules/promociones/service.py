"""PromocionesService — regla de negocio de promociones inteligentes (feature 005).

Orquesta el motor de afinidad (`analytics/afinidad.py`), el cupón de afinidad
(reutiliza `campanas`/`cupon_enviado`/`cupon_redimido` de 002 + `sendgrid_client`),
la clasificación ABC (`analytics/clasificacion_abc.py`), la liquidación de
categoría C y la colocación promocional. Consulta de solo lectura contra
`propuesta_ajuste_precio` de 003 (FR-013). El router sólo traduce HTTP ↔ estos
métodos (Principio V/XI).
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from src.integrations import sendgrid_client
from src.modules.promociones.analytics import afinidad, clasificacion_abc
from src.modules.promociones.repository import PromocionesRepository
from src.modules.promociones.schemas import ColocacionIn
from src.shared.exceptions import ConflictError, NotFoundError

logger = logging.getLogger("sira.promociones")

VENTANA_AFINIDAD_DIAS = 365
VENTANA_ABC_DIAS = 90
SEMANAS_ROTACION_LOCAL = 4
_DEF_SOPORTE = Decimal("0.02")
_DEF_CONFIANZA = Decimal("0.30")
_DEF_VIGENCIA_CUPON = Decimal("30")
_DEF_ROTACION_MIN = Decimal("1.0")
_DEF_DESCUENTO_LIQ = Decimal("25.0")


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PromocionesService:
    def __init__(self, repo: PromocionesRepository) -> None:
        self.repo = repo

    # ==================================================== US1: afinidad
    async def calcular_afinidad(self) -> dict:
        """FR-001 / research.md Decisión 1/3 — job mensual: recalcula el conjunto
        de reglas de asociación, reemplazando las `vigente` anteriores."""
        soporte = float(await self.repo.valor_config("soporte_minimo_regla", _DEF_SOPORTE))
        confianza = float(await self.repo.valor_config("confianza_minima_regla", _DEF_CONFIANZA))

        lineas = await self.repo.lineas_para_afinidad()
        matriz = afinidad.matriz_transacciones(lineas)
        reglas = afinidad.calcular_reglas(matriz, soporte, confianza)

        # descarta reglas cuyos productos ya no están activos (Edge Case)
        activos = await self.repo.productos_activos_ids()
        reglas = [r for r in reglas if r["antecedente"] in activos and r["consecuente"] in activos]

        n = await self.repo.reemplazar_reglas(reglas)
        logger.info("calcular_afinidad: %d reglas vigentes nuevas", n)
        return {"reglas_generadas": n, "transacciones_evaluadas": int(len(matriz))}

    async def listar_reglas(self, estado: str | None = None):
        from src.models.regla_afinidad import ReglaAfinidad

        stmt = self.repo.reglas_query(estado=estado).order_by(ReglaAfinidad.confianza.desc())
        reglas = list((await self.repo.session.scalars(stmt)).all())
        ids = {r.product_id_antecedente for r in reglas} | {
            r.product_id_consecuente for r in reglas
        }
        nombres = await self.repo.nombres_productos(ids)
        salida = []
        for r in reglas:
            fila = {
                c.name: getattr(r, c.name) for c in ReglaAfinidad.__table__.columns
            }
            fila["product_nombre_antecedente"] = nombres.get(r.product_id_antecedente)
            fila["product_nombre_consecuente"] = nombres.get(r.product_id_consecuente)
            salida.append(fila)
        return salida

    async def desactivar_regla(self, regla_id: int, empleado_id: int, motivo: str | None):
        """FR-002 — desactivación manual persistente (no se reactiva sola)."""
        regla = await self.repo.get_regla(regla_id)
        if regla is None:
            raise NotFoundError(f"Regla {regla_id} no existe")
        if regla.estado != "vigente":
            raise ConflictError(f"La regla {regla_id} ya está '{regla.estado}'")
        regla.estado = "desactivada"
        regla.desactivada_por = empleado_id
        regla.fecha_desactivacion = _ahora()
        regla.motivo_desactivacion = motivo
        await self.repo.flush()
        return regla

    async def recomendar_cross_sell(self, product_ids: list[int]) -> dict:
        """FR-003/FR-004/FR-005 — la recomendación de mayor confianza cuyo
        antecedente está en el carrito y cuyo consecuente no."""
        reglas = await self.repo.reglas_vigentes()
        mejor = afinidad.mejor_recomendacion(reglas, set(product_ids))
        if mejor is None:
            return {"recomendacion_disponible": False}
        return {
            "recomendacion_disponible": True,
            "product_id_recomendado": mejor["consecuente"],
            "confianza": Decimal(str(mejor["confianza"])),
        }

    # ==================================================== US2: cupón de afinidad
    async def evaluar_venta_para_afinidad(self, venta_id: int) -> dict:
        """FR-006/FR-007 — al cerrar una venta de un cliente identificado con
        consentimiento, si contiene el antecedente de una regla vigente sin el
        consecuente, envía un cupón para el consecuente (sin duplicar dentro de la
        ventana de vigencia)."""
        venta = await self.repo.venta_para_afinidad(venta_id)
        if venta is None:
            raise NotFoundError(f"Venta {venta_id} no existe")
        if venta["household_id"] is None:
            return {"cupones_generados": 0}
        if not await self.repo.cliente_con_consentimiento(venta["household_id"]):
            return {"cupones_generados": 0}  # FR-006 sólo con consentimiento

        carrito = venta["product_ids"]
        reglas = await self.repo.reglas_vigentes()
        aplicables = [
            r for r in reglas if r["antecedente"] in carrito and r["consecuente"] not in carrito
        ]
        if not aplicables:
            return {"cupones_generados": 0}

        vigencia_dias = int(
            await self.repo.valor_config("vigencia_cupon_afinidad_dias", _DEF_VIGENCIA_CUPON)
        )
        desde = _ahora() - timedelta(days=vigencia_dias)
        campaign_id = await self.repo.campana_afinidad(date.today())

        generados = 0
        for regla in aplicables:
            if await self.repo.cupon_afinidad_vigente(
                venta["household_id"], regla["regla_id"], desde
            ):
                continue  # FR-007
            coupon_upc = f"AFIN{regla['regla_id']}H{venta['household_id']}"
            await self.repo.registrar_cupon(coupon_upc, regla["consecuente"], campaign_id)
            entregado = self._enviar_correo(venta["household_id"], coupon_upc, regla["consecuente"])
            await self.repo.registrar_cupon_afinidad(
                household_id=venta["household_id"],
                coupon_upc=coupon_upc,
                campaign_id=campaign_id,
                regla_id=regla["regla_id"],
                entregado=entregado,
            )
            generados += 1
        await self.repo.flush()
        return {"cupones_generados": generados}

    @staticmethod
    def _enviar_correo(household_id: int, coupon_upc: str, product_id: int) -> bool:
        """Best-effort (Principio II): un fallo de SendGrid deja `entregado = false`
        pero el cupón y su envío quedan registrados igual."""
        try:
            return sendgrid_client.enviar_correo(
                to=f"anon-{household_id}@cliente.local",
                subject="Un descuento para completar tu compra 🛒",
                html=(
                    f"<p>Notamos que este producto suele comprarse junto con otro. "
                    f"Te dejamos el cupón <strong>{coupon_upc}</strong> para el producto "
                    f"#{product_id} en tu próxima visita.</p>"
                ),
            )
        except Exception:  # noqa: BLE001
            logger.info("SendGrid no disponible para el cupón de afinidad %s", coupon_upc)
            return False

    async def listar_cupones_afinidad(self, household_id: int | None = None) -> list[dict]:
        stmt = self.repo.cupones_afinidad_query(household_id=household_id)
        filas = (await self.repo.session.execute(stmt)).all()
        salida = []
        for envio, product_id in filas:
            salida.append(
                {
                    "envio_id": envio.envio_id,
                    "household_id": envio.household_id,
                    "product_id_ofrecido": product_id,
                    "regla_afinidad_id": envio.regla_afinidad_id,
                    "fecha_envio": envio.fecha_envio,
                    "entregado": envio.entregado,
                    "redimido": await self.repo.redimido(envio.coupon_upc, envio.household_id),
                }
            )
        return salida

    async def tasa_redencion_afinidad(self) -> dict:
        enviados, redimidos = await self.repo.tasa_redencion_afinidad()
        return {
            "enviados": enviados,
            "redimidos": redimidos,
            "tasa_pct": round(100 * redimidos / enviados, 2) if enviados else 0.0,
        }

    # ==================================================== US3: ABC + liquidación
    async def clasificar_abc(self) -> dict:
        """FR-009/FR-010 — job mensual: reclasifica todo el catálogo por valor de
        venta acumulado (Pareto) dentro de cada categoría, y registra los cambios."""
        desde = date.today() - timedelta(days=VENTANA_ABC_DIAS)
        por_categoria = await self.repo.valor_venta_por_categoria(desde)
        actual = await self.repo.clasificacion_actual()

        cambios = []
        for _categoria, valores in por_categoria.items():
            nuevas = clasificacion_abc.clasificar_categoria(valores)
            for product_id, nueva in nuevas.items():
                anterior = actual.get(product_id)
                if (anterior or None) != nueva:
                    cambios.append({"product_id": product_id, "anterior": anterior, "nueva": nueva})
        await self.repo.aplicar_clasificacion(cambios, _ahora())
        return {"productos_reclasificados": len(cambios)}

    async def listar_cambios_abc(self, cambios_desde: datetime | None) -> list:
        if cambios_desde is None:
            cambios_desde = await self.repo.ultima_fecha_clasificacion()
        if cambios_desde is None:
            return []
        # incluye la propia corrida (>=), restando un microsegundo por si empatan
        return await self.repo.cambios_abc(cambios_desde - timedelta(seconds=1))

    async def regla_liquidacion(self) -> dict:
        return {
            "rotacion_minima_liquidacion_semanal": await self.repo.valor_config(
                "rotacion_minima_liquidacion_semanal", _DEF_ROTACION_MIN
            ),
            "descuento_liquidacion_pct": await self.repo.valor_config(
                "descuento_liquidacion_pct", _DEF_DESCUENTO_LIQ
            ),
        }

    async def actualizar_regla_liquidacion(self, *, rotacion=None, descuento=None) -> dict:
        if rotacion is not None:
            fila = await self.repo.get_config("rotacion_minima_liquidacion_semanal")
            if fila is not None:
                fila.valor = rotacion
        if descuento is not None:
            fila = await self.repo.get_config("descuento_liquidacion_pct")
            if fila is not None:
                fila.valor = descuento
        await self.repo.flush()
        return await self.regla_liquidacion()

    async def generar_candidatos_liquidacion(
        self, semana: int | None = None, anio: int | None = None
    ) -> dict:
        """FR-012/FR-013 — job semanal: productos categoría C con rotación local
        bajo el umbral, excluyendo los que tienen ajuste de precio pendiente en 003."""
        iso = date.today().isocalendar()
        semana = semana or iso.week
        anio = anio or iso.year

        c_ids = await self.repo.product_ids_categoria_c()
        pendientes = await self.repo.product_ids_con_precio_pendiente()
        elegibles = clasificacion_abc.excluir_con_precio_pendiente(c_ids, pendientes)
        if not elegibles:
            return {"candidatos_generados": 0}

        umbral = float(
            await self.repo.valor_config("rotacion_minima_liquidacion_semanal", _DEF_ROTACION_MIN)
        )
        descuento = float(
            await self.repo.valor_config("descuento_liquidacion_pct", _DEF_DESCUENTO_LIQ)
        )
        desde = date.today() - timedelta(weeks=SEMANAS_ROTACION_LOCAL)
        rotaciones = await self.repo.rotacion_local(elegibles, desde)

        generados = 0
        for (product_id, tienda_id), unidades in rotaciones.items():
            rotacion_semanal = unidades / SEMANAS_ROTACION_LOCAL
            if rotacion_semanal >= umbral:
                continue
            await self.repo.upsert_candidato(
                {
                    "product_id": product_id,
                    "tienda_id": tienda_id,
                    "semana": semana,
                    "anio": anio,
                    "rotacion_reciente_calculada": round(rotacion_semanal, 2),
                    "descuento_sugerido_pct": descuento,
                    "estado": "candidato",
                }
            )
            generados += 1
        await self.repo.flush()
        return {"candidatos_generados": generados}

    async def listar_candidatos(self, *, tienda_id: int, semana=None, anio=None):
        from src.models.candidato_liquidacion import CandidatoLiquidacion

        iso = date.today().isocalendar()
        stmt = self.repo.candidatos_query(
            tienda_id=tienda_id, semana=semana or iso.week, anio=anio or iso.year
        ).order_by(CandidatoLiquidacion.rotacion_reciente_calculada)
        return list((await self.repo.session.scalars(stmt)).all())

    async def ejecutar_candidato(self, candidato_id: int, empleado_id: int):
        """FR-014 — el Encargado de Tienda ejecuta la liquidación de un candidato."""
        candidato = await self.repo.get_candidato(candidato_id)
        if candidato is None:
            raise NotFoundError(f"Candidato {candidato_id} no existe")
        if candidato.estado != "candidato":
            raise ConflictError(f"El candidato {candidato_id} ya está '{candidato.estado}'")
        candidato.estado = "ejecutado"
        candidato.fecha_ejecucion = _ahora()
        candidato.ejecutado_por = empleado_id
        await self.repo.flush()
        return candidato

    # ==================================================== US4: colocación
    async def registrar_colocacion(self, data: ColocacionIn) -> dict:
        promocion_id = await self.repo.crear_colocacion(data.model_dump())
        colocaciones = await self.repo.colocaciones(
            tienda_id=data.tienda_id, semana=data.semana, anio=data.anio
        )
        return next(c for c in colocaciones if c["promocion_id"] == promocion_id)

    async def listar_colocaciones(self, *, tienda_id=None, semana=None, anio=None) -> list[dict]:
        return await self.repo.colocaciones(tienda_id=tienda_id, semana=semana, anio=anio)

    async def buscar_productos(self, search: str | None) -> list[dict]:
        return await self.repo.buscar_productos(search)

    async def listar_tiendas(self) -> list[dict]:
        return await self.repo.tiendas_activas()

    async def efecto_colocacion(self, promocion_id: int) -> dict:
        """FR-016 — ventas de la semana de colocación vs. una semana de referencia
        sin colocación (la semana anterior), sin atribución causal automática."""
        col = await self.repo.get_colocacion(promocion_id)
        if col is None:
            raise NotFoundError(f"Colocación {promocion_id} no existe")
        semana_ref = col["semana"] - 1 if col["semana"] > 1 else col["semana"] + 1
        return {
            "ventas_semana_colocacion": await self.repo.unidades_producto_semana(
                col["product_id"], col["tienda_id"], col["semana"], col["anio"]
            ),
            "ventas_semana_referencia": await self.repo.unidades_producto_semana(
                col["product_id"], col["tienda_id"], semana_ref, col["anio"]
            ),
        }

    # ==================================================== configuración
    async def listar_configuracion(self):
        return await self.repo.listar_configuracion()
