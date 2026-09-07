"""ClientesService — regla de negocio del módulo Clientes/Fidelización (feature 002).

US1: alta con captura de consentimiento, actualización (incl. revocar/otorgar
consentimiento sin anonimizar), y baja con anonimización real que conserva
`household_id` (FR-001/FR-002/FR-003).

`recalcular_clv_churn` (job semanal) calcula CLV (US2) + churn/severidad (US3);
`generar_eventos_hito` (job diario) genera los hitos y dispara el cupón (US4).
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from src.integrations import sendgrid_client
from src.models.cliente import Cliente
from src.models.cliente_demografico import ClienteDemografico
from src.models.nivel_fidelizacion import NivelFidelizacion
from src.modules.clientes.repository import ClientesRepository
from src.modules.clientes.schemas import ClienteIn, ClientePatch, DatosDemograficosIn
from src.shared.churn import ciclo_compra_dias, score_churn, severidad
from src.shared.clv import VENTANA_DIAS, clv_score, percentil_95
from src.shared.cupon_hito import seleccionar_producto_ancla
from src.shared.exceptions import BusinessRuleError, ConflictError, NotFoundError

logger = logging.getLogger("sira.clientes")


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ClientesService:
    def __init__(self, repo: ClientesRepository) -> None:
        self.repo = repo

    # ------------------------------------------------------------------ US1
    async def registrar_cliente(self, data: ClienteIn) -> Cliente:
        if await self.repo.existe_email(data.email):
            raise ConflictError(f"Ya existe un cliente con el email {data.email}")
        if data.documento_identidad and await self.repo.existe_documento(data.documento_identidad):
            raise ConflictError(f"Ya existe un cliente con el documento {data.documento_identidad}")

        cliente = Cliente(
            nombre=data.nombre,
            email=data.email,
            telefono=data.telefono,
            documento_identidad=data.documento_identidad or None,
            fecha_nacimiento=data.fecha_nacimiento,
            consentimiento_datos=data.consentimiento_datos,
            fecha_consentimiento_datos=_ahora(),
            activo=True,
        )
        self.repo.agregar(cliente)
        await self.repo.flush()
        await self.repo.refrescar(cliente)

        if data.datos_demograficos is not None:
            await self._upsert_demografico(cliente.household_id, data.datos_demograficos)
            await self.repo.flush()
        return cliente

    async def actualizar_cliente(self, household_id: int, data: ClientePatch) -> Cliente:
        cliente = await self.repo.get_cliente(household_id)
        if cliente is None:
            raise NotFoundError(f"Cliente {household_id} no existe")

        campos = data.model_dump(exclude_unset=True)

        if "email" in campos and campos["email"] != cliente.email:
            if await self.repo.existe_email(campos["email"], excepto=household_id):
                raise ConflictError(f"El email {campos['email']} ya está en uso")
            cliente.email = campos["email"]
        if "documento_identidad" in campos:
            doc = campos["documento_identidad"] or None
            if doc and await self.repo.existe_documento(doc, excepto=household_id):
                raise ConflictError(f"El documento {doc} ya está en uso")
            cliente.documento_identidad = doc
        if "nombre" in campos:
            cliente.nombre = campos["nombre"]
        if "telefono" in campos:
            cliente.telefono = campos["telefono"]
        if "fecha_nacimiento" in campos:
            cliente.fecha_nacimiento = campos["fecha_nacimiento"]
        if "consentimiento_datos" in campos and campos["consentimiento_datos"] is not None:
            # FR-002: revocar/otorgar sin anonimizar; sólo cambia el gating hacia adelante.
            cliente.consentimiento_datos = campos["consentimiento_datos"]
            cliente.fecha_consentimiento_datos = _ahora()

        cliente.updated_at = _ahora()
        if data.datos_demograficos is not None:
            await self._upsert_demografico(household_id, data.datos_demograficos)

        await self.repo.flush()
        return cliente

    async def dar_de_baja(self, household_id: int) -> Cliente:
        cliente = await self.repo.get_cliente(household_id)
        if cliente is None:
            raise NotFoundError(f"Cliente {household_id} no existe")

        # FR-003 / research.md §5: anonimización REAL (UPDATE), conserva household_id
        # para no romper la FK de ventas/CLV/churn históricos. Nunca un DELETE físico.
        cliente.nombre = "CLIENTE ANONIMIZADO"
        cliente.email = f"anon-{household_id}@anonimizado.local"
        cliente.telefono = None
        cliente.fecha_nacimiento = None
        cliente.documento_identidad = None
        cliente.activo = False
        cliente.updated_at = _ahora()
        await self.repo.flush()
        return cliente

    async def _upsert_demografico(self, household_id: int, data: DatosDemograficosIn) -> None:
        demo = await self.repo.get_demografico(household_id)
        campos = data.model_dump(exclude_unset=True)
        if demo is None:
            self.repo.agregar(ClienteDemografico(household_id=household_id, **campos))
        else:
            for k, v in campos.items():
                setattr(demo, k, v)

    async def listar(self, params, **filtros):
        stmt = self.repo.clientes_query(**filtros)
        return await self.repo.paginate(params, stmt=stmt, order_by=Cliente.household_id.desc())

    # ============================================================ US2: CLV
    def nivel_para_score(self, score: Decimal, niveles: list[NivelFidelizacion]) -> int | None:
        """FR-006/FR-008: el nivel más alto cuyo `umbral_clv_min` no supera el score."""
        elegibles = [n for n in niveles if Decimal(str(n.umbral_clv_min)) <= score]
        if not elegibles:
            return None
        return max(elegibles, key=lambda n: Decimal(str(n.umbral_clv_min))).nivel_id

    async def reclasificar_nivel(self, household_id: int) -> int | None:
        """Recalcula el nivel del cliente contra su CLV más reciente y los
        umbrales vigentes (FR-008). Devuelve el `nivel_id` asignado."""
        clv = await self.repo.ultimo_clv(household_id)
        if clv is None:
            return None
        niveles = await self.repo.niveles()
        nivel_id = self.nivel_para_score(Decimal(str(clv.clv_score)), niveles)
        if nivel_id != clv.nivel_id:
            clv.nivel_id = nivel_id
            await self.repo.flush()
        return nivel_id

    async def recalcular_clv(self, fecha: date | None = None) -> dict:
        """FR-005: CLV compuesto semanal (frecuencia + margen real, nunca gasto
        bruto). Sólo clientes elegibles con >= 1 compra en la ventana de 180 días."""
        fecha = fecha or date.today()
        desde = datetime.combine(fecha, datetime.min.time()) - timedelta(days=VENTANA_DIAS)
        por_cliente = await self.repo.compras_y_margen_en_ventana(desde)
        if not por_cliente:
            return {"clientes_con_clv": 0}

        freqs = [float(compras) for compras, _ in por_cliente.values()]
        margenes = [float(margen) for _, margen in por_cliente.values()]
        freq_p95 = percentil_95(freqs)
        margen_p95 = percentil_95(margenes)

        niveles = await self.repo.niveles()
        calculados = 0
        for household_id, (compras, margen) in por_cliente.items():
            if compras < 1:
                continue
            score = clv_score(float(compras), float(margen), freq_p95, margen_p95)
            nivel_id = self.nivel_para_score(score, niveles)
            await self.repo.upsert_clv(household_id, score, nivel_id, fecha)
            calculados += 1
        await self.repo.flush()
        return {
            "clientes_con_clv": calculados,
            "frecuencia_p95": freq_p95,
            "margen_p95": margen_p95,
        }

    async def listar_niveles(self) -> list[NivelFidelizacion]:
        return await self.repo.niveles()

    async def ajustar_umbral_nivel(self, nivel_id: int, umbral: Decimal) -> NivelFidelizacion:
        nivel = await self.repo.get_nivel(nivel_id)
        if nivel is None:
            raise NotFoundError(f"Nivel {nivel_id} no existe")
        if umbral < 0:
            raise BusinessRuleError("El umbral no puede ser negativo")
        nivel.umbral_clv_min = umbral
        await self.repo.flush()
        return nivel

    # ========================================================== US3: churn
    async def recalcular_churn(self, fecha: date | None = None) -> dict:
        """FR-009/FR-010: ciclo de compra individual + severidad relativa a ese
        ciclo (nunca un umbral fijo). Sólo clientes elegibles con >= 2 compras."""
        fecha = fecha or date.today()
        por_cliente = await self.repo.fechas_compra_por_cliente()
        calculados = en_riesgo = inactivos = 0
        for household_id, fechas in por_cliente.items():
            ciclo = ciclo_compra_dias(fechas)
            if ciclo is None:
                continue
            dias = (fecha - max(fechas)).days
            sev = severidad(dias, ciclo)
            await self.repo.upsert_churn(
                household_id, score_churn(dias, ciclo), round(ciclo), sev, fecha
            )
            calculados += 1
            en_riesgo += sev == "en_riesgo"
            inactivos += sev == "inactivo"
        await self.repo.flush()
        return {
            "clientes_con_churn": calculados,
            "en_riesgo": en_riesgo,
            "inactivos": inactivos,
        }

    async def listar_riesgo_fuga(self, params, *, severidad: str | None = None) -> dict:
        """FR-011 / SC-005: el Jefe de Marketing nunca calcula esto a mano — cada
        fila trae `ciclo_compra_dias` y `dias_desde_ultima_compra` ya resueltos."""
        hoy = date.today()
        total, filas = await self.repo.riesgo_fuga_pagina(
            severidad=severidad, offset=params.offset, limit=params.limit
        )
        items = [
            {
                "household_id": churn.household_id,
                "nombre": nombre,
                "documento_identidad": documento,
                "score": churn.score,
                "severidad": churn.severidad,
                "ciclo_compra_dias": churn.ciclo_compra_dias,
                "dias_desde_ultima_compra": await self.repo.dias_desde_ultima_compra(
                    churn.household_id, hoy
                ),
                "fecha_calculo": churn.fecha_calculo,
            }
            for churn, nombre, documento in filas
        ]
        return {"items": items, "total": total, "page": params.page, "size": params.size}

    # --------------------------------------------- jobs periódicos
    async def recalcular_clv_churn(self) -> dict:
        """Job semanal: CLV (US2) + churn/severidad (US3)."""
        elegibles = await self.repo.household_ids_elegibles()
        clv = await self.recalcular_clv()
        churn = await self.recalcular_churn()
        logger.info(
            "recalcular_clv_churn: %d elegibles, clv=%s churn=%s", len(elegibles), clv, churn
        )
        return {"clientes_elegibles": len(elegibles), **clv, **churn}

    # ================================================= US4: campañas por hito
    async def generar_eventos_hito(self, fecha: date | None = None) -> dict:
        """Job diario (FR-012/FR-013): por cada cliente elegible que cumple años o
        aniversario de registro hoy, crea el `eventos_cliente` y dispara un cupón
        de hito (producto ancla de mayor margen). Idempotente: no duplica el
        evento si ya se generó hoy. Una falla de SendGrid no aborta nada
        (Principio II) — sólo deja `entregado = false`."""
        fecha = fecha or date.today()
        pendientes = await self.repo.clientes_con_hito(fecha)
        if not pendientes:
            return {"eventos_generados": 0, "cupones_enviados": 0}

        product_id = seleccionar_producto_ancla(await self.repo.productos_ancla())
        campaign_id = await self.repo.campana_hito(fecha)

        eventos = cupones = 0
        for cliente, tipo_evento in pendientes:
            if await self.repo.evento_existe(cliente.household_id, tipo_evento, fecha):
                continue
            evento = await self.repo.crear_evento(cliente.household_id, tipo_evento, fecha)
            eventos += 1
            if product_id is None:
                # Sin producto ancla configurado no hay cupón, pero el evento
                # queda registrado igual (FR-012 no depende de FR-013).
                continue
            coupon_upc = f"HITO{evento.evento_id}"
            await self.repo.registrar_cupon(coupon_upc, product_id, campaign_id)
            entregado = self._enviar_cupon_hito(cliente, tipo_evento, coupon_upc)
            await self.repo.registrar_cupon_enviado(
                evento_id=evento.evento_id,
                household_id=cliente.household_id,
                coupon_upc=coupon_upc,
                campaign_id=campaign_id,
                entregado=entregado,
            )
            cupones += 1

        await self.repo.flush()
        return {"eventos_generados": eventos, "cupones_enviados": cupones}

    @staticmethod
    def _enviar_cupon_hito(cliente: Cliente, tipo_evento: str, coupon_upc: str) -> bool:
        if not cliente.email:
            return False
        motivo = "cumpleaños" if tipo_evento == "cumpleanos" else "aniversario con nosotros"
        return sendgrid_client.enviar_correo(
            to=cliente.email,
            subject=f"Un regalo por tu {motivo} 🎁",
            html=(
                f"<p>Hola {cliente.nombre or ''},</p>"
                f"<p>Por tu {motivo} te enviamos el cupón <strong>{coupon_upc}</strong>. "
                f"Preséntalo en caja en tu próxima compra.</p>"
            ),
        )

    async def registrar_redencion(
        self, coupon_upc: str, household_id: int, campaign_id: int
    ) -> None:
        """FR-015: el cajero registra que un cliente usó su cupón en caja."""
        if not await self.repo.es_elegible(household_id):
            # Un cliente sin consentimiento / dado de baja no debería llegar aquí,
            # pero si llega no se le perfila (FR-001).
            raise BusinessRuleError("El cliente no está habilitado para campañas")
        await self.repo.registrar_redencion(
            household_id=household_id,
            coupon_upc=coupon_upc,
            campaign_id=campaign_id,
            fecha=date.today(),
        )

    async def tasa_redencion(self, tipo_evento: str | None = None) -> list[dict]:
        """FR-014: redimidos / enviados, agrupado por tipo de evento de hito."""
        filas = await self.repo.tasa_redencion_por_hito(tipo_evento)
        return [
            {
                "tipo_evento": tipo,
                "enviados": enviados,
                "redimidos": redimidos,
                "tasa": round(redimidos / enviados, 4) if enviados else 0.0,
            }
            for tipo, enviados, redimidos in filas
        ]

    async def eventos_de_cliente(self, household_id: int) -> list[dict]:
        cliente = await self.repo.get_cliente(household_id)
        if cliente is None:
            raise NotFoundError(f"Cliente {household_id} no existe")
        return [
            {
                "evento_id": evento.evento_id,
                "tipo_evento": evento.tipo_evento,
                "fecha": evento.fecha,
                "cupon_enviado": coupon_upc,
                "entregado": entregado,
                "redimido": bool(redimido),
            }
            for evento, coupon_upc, entregado, redimido in await self.repo.eventos_de_cliente(
                household_id
            )
        ]
