"""CampanasService — campañas de reactivación con grupo de control y uplift (US5).

Reglas duras del spec:
  - FR-017 / SC-004: una campaña de reactivación no se envía sin un grupo de
    control definido — se valida en `enviar`, nunca sólo en el frontend.
  - FR-018: el uplift al cierre compara la **tasa de retorno** de tratado vs
    control, jamás la tasa de redención del cupón.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from src.integrations import sendgrid_client
from src.models.campana import Campana
from src.models.campana_resultado import CampanaResultado
from src.modules.clientes.campanas_repository import CampanasRepository
from src.shared.cupon_hito import seleccionar_producto_ancla
from src.shared.exceptions import BusinessRuleError, ConflictError, NotFoundError
from src.shared.uplift import tasa_retorno

logger = logging.getLogger("sira.campanas")

_GRUPOS = {"tratado", "control"}
_DECISIONES = {"aprobada_escalar", "descartada"}


class CampanasService:
    def __init__(self, repo: CampanasRepository) -> None:
        self.repo = repo

    async def crear_reactivacion(self, data) -> Campana:
        if data.categoria_sira != "reactivacion":
            raise BusinessRuleError("categoria_sira debe ser 'reactivacion'")
        if data.end_date < data.start_date:
            raise BusinessRuleError("end_date no puede ser anterior a start_date")

        miembros = await self._resolver_miembros(data)
        if not miembros:
            raise BusinessRuleError("La campaña necesita al menos un miembro")

        household_ids = [hid for hid, _ in miembros]
        if len(set(household_ids)) != len(household_ids):
            raise BusinessRuleError("Un cliente no puede figurar dos veces en la campaña")
        for _, grupo in miembros:
            if grupo not in _GRUPOS:
                raise BusinessRuleError(f"grupo inválido: {grupo}")

        no_elegibles = await self.repo.household_ids_no_elegibles(household_ids)
        if no_elegibles:
            raise BusinessRuleError(
                f"Clientes fuera del alcance de campañas (sin consentimiento o inactivos): "
                f"{no_elegibles}"
            )

        campana = await self.repo.crear_campana(
            start_date=data.start_date,
            end_date=data.end_date,
            categoria_sira="reactivacion",
            nombre=getattr(data, "nombre", None),
        )
        await self.repo.agregar_miembros(campana.campaign_id, miembros)
        return campana

    async def _resolver_miembros(self, data) -> list[tuple[int, str]]:
        """Miembros explícitos, o un `segmento` predefinido → split 80/20
        tratado/control determinista (por household_id)."""
        if data.miembros:
            return [(m.household_id, m.grupo) for m in data.miembros]
        if not getattr(data, "segmento", None):
            return []
        from src.modules.clientes.directorio_repository import DirectorioRepository

        ids = await DirectorioRepository(self.repo.session).household_ids_de_segmento(
            data.segmento
        )
        if not ids:
            raise BusinessRuleError(f"El segmento '{data.segmento}' no tiene clientes elegibles")
        ids = sorted(ids)
        # ~20% al grupo de control (los primeros), mínimo 1 de cada grupo si hay ≥2.
        n_control = max(1, round(len(ids) * 0.2)) if len(ids) >= 2 else 0
        return [
            (hid, "control" if i < n_control else "tratado") for i, hid in enumerate(ids)
        ]

    async def _campana_reactivacion(self, campaign_id: int) -> Campana:
        campana = await self.repo.get_campana(campaign_id)
        if campana is None:
            raise NotFoundError(f"Campaña {campaign_id} no existe")
        if campana.categoria_sira != "reactivacion":
            raise BusinessRuleError("La campaña no es de reactivación")
        return campana

    async def enviar(self, campaign_id: int) -> dict:
        await self._campana_reactivacion(campaign_id)
        if await self.repo.campana_enviada(campaign_id):
            raise ConflictError("La campaña ya fue enviada")

        miembros = await self.repo.miembros(campaign_id)
        if any(m.grupo is None for m in miembros):
            raise BusinessRuleError("Todos los miembros deben tener grupo asignado antes del envío")
        grupos = {m.grupo for m in miembros}
        if "control" not in grupos:
            # FR-017 (requisito duro): sin grupo de control no hay forma de medir uplift.
            raise BusinessRuleError(
                "La campaña no tiene grupo de control — no se puede enviar (FR-017)"
            )
        tratados = [m.household_id for m in miembros if m.grupo == "tratado"]
        if not tratados:
            raise BusinessRuleError("La campaña no tiene ningún miembro en el grupo tratado")

        product_id = seleccionar_producto_ancla(await self.repo.productos_ancla())
        coupon_upc = f"REACT{campaign_id}"
        entregado: dict[int, bool] = {}
        if product_id is not None:
            await self.repo.registrar_cupon(coupon_upc, product_id, campaign_id)
            clientes = await self.repo.clientes_por_ids(tratados)
            for hid in tratados:
                cliente = clientes.get(hid)
                entregado[hid] = self._enviar_incentivo(cliente, coupon_upc) if cliente else False
        await self.repo.registrar_envios(
            campaign_id=campaign_id,
            coupon_upc=coupon_upc,
            household_ids=tratados,
            entregado=entregado,
        )
        return {
            "enviados": len(tratados),
            "coupon_upc": coupon_upc if product_id is not None else None,
        }

    @staticmethod
    def _enviar_incentivo(cliente, coupon_upc: str) -> bool:
        if not cliente.email:
            return False
        return sendgrid_client.enviar_correo(
            to=cliente.email,
            subject="Te extrañamos — un incentivo para tu próxima compra",
            html=(
                f"<p>Hola {cliente.nombre or ''},</p>"
                f"<p>Queremos verte de vuelta. Usa el cupón <strong>{coupon_upc}</strong> "
                f"en tu próxima compra.</p>"
            ),
        )

    async def cerrar(self, campaign_id: int) -> CampanaResultado:
        campana = await self._campana_reactivacion(campaign_id)
        if not await self.repo.campana_enviada(campaign_id):
            raise ConflictError("La campaña aún no fue enviada")
        if await self.repo.get_resultado(campaign_id) is not None:
            raise ConflictError("La campaña ya fue cerrada")

        desde = await self.repo.fecha_envio(campaign_id) or datetime.combine(
            campana.start_date, datetime.min.time()
        )
        retorno = await self.repo.retorno_por_grupo(campaign_id, desde)
        t_total, t_volvieron = retorno.get("tratado", (0, 0))
        c_total, c_volvieron = retorno.get("control", (0, 0))

        return await self.repo.crear_resultado(
            campaign_id=campaign_id,
            tasa_tratado=tasa_retorno(t_volvieron, t_total),
            tasa_control=tasa_retorno(c_volvieron, c_total),
            fecha=date.today(),
        )

    async def decidir(
        self, campaign_id: int, decision: str, empleado_id: int | None
    ) -> CampanaResultado:
        if decision not in _DECISIONES:
            raise BusinessRuleError(f"decisión inválida: {decision}")
        resultado = await self.repo.get_resultado(campaign_id)
        if resultado is None:
            raise BusinessRuleError(
                "La campaña no está cerrada — no hay uplift sobre el cual decidir"
            )
        await self.repo.set_decision(resultado, decision, empleado_id)
        return resultado

    async def detalle(self, campaign_id: int) -> dict:
        campana = await self._campana_reactivacion(campaign_id)
        miembros = await self.repo.miembros(campaign_id)
        resultado = await self.repo.get_resultado(campaign_id)
        return {
            "campaign_id": campana.campaign_id,
            "categoria_sira": campana.categoria_sira,
            "nombre": campana.nombre,
            "start_date": campana.start_date,
            "end_date": campana.end_date,
            "enviada": await self.repo.campana_enviada(campaign_id),
            "miembros": [{"household_id": m.household_id, "grupo": m.grupo} for m in miembros],
            "resultado": (
                None
                if resultado is None
                else {
                    "tasa_retorno_tratado": resultado.tasa_retorno_tratado,
                    "tasa_retorno_control": resultado.tasa_retorno_control,
                    "uplift": resultado.uplift,
                    "decision": resultado.decision,
                    "fecha_calculo": resultado.fecha_calculo,
                }
            ),
        }

    async def listar(self, params, *, categoria_sira: str | None = None):
        stmt = self.repo.campanas_query(categoria_sira=categoria_sira)
        return await self.repo.paginate(params, stmt=stmt, order_by=Campana.campaign_id.desc())
