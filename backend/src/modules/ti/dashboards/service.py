"""Servicio de `ti/dashboards` (feature 009, US2/US3).

No recalcula KPIs (Principio VIII) — devuelve el último snapshot publicado por
los jobs. El alcance por departamento (FR-005) se valida aquí, en la capa de
servicio, igual que el alcance por tienda de 012: cada `Jefe_*` sólo ve el
dashboard táctico de su propio módulo; `Gerente_General` los ve todos.
"""

from __future__ import annotations

from src.core.security import Principal
from src.modules.ti.dashboards.repository import TiDashboardsRepository
from src.shared.dashboards import (
    MODULOS_TACTICOS,
    ROL_A_MODULO_TACTICO,
    ROL_LECTURA_GLOBAL,
)
from src.shared.exceptions import ForbiddenError, NotFoundError


class TiDashboardsService:
    def __init__(self, repo: TiDashboardsRepository) -> None:
        self.repo = repo

    # ============================================================ US2: dashboard táctico
    async def dashboard_tactico(self, modulo_nombre: str, principal: Principal) -> dict:
        if modulo_nombre not in MODULOS_TACTICOS:
            raise NotFoundError(f"'{modulo_nombre}' no es un departamento con dashboard táctico")
        self._verificar_alcance(modulo_nombre, principal)

        modulo_id = await self.repo.modulo_id_por_nombre(modulo_nombre)
        publicacion = (
            await self.repo.ultima_publicacion_tactica(modulo_id) if modulo_id is not None else None
        )
        if publicacion is None:
            raise NotFoundError(
                f"Todavía no se ha publicado el dashboard táctico de {modulo_nombre}"
            )
        return {
            "publicacion_id": publicacion.publicacion_id,
            "fecha_publicacion": publicacion.fecha_hora,
            "kpis": await self.repo.kpis_de(publicacion.publicacion_id),
        }

    @staticmethod
    def _verificar_alcance(modulo_nombre: str, principal: Principal) -> None:
        if principal.rol == ROL_LECTURA_GLOBAL:
            return
        propio = ROL_A_MODULO_TACTICO.get(principal.rol or "")
        if propio != modulo_nombre:
            raise ForbiddenError(
                "Cada Jefe de departamento sólo consulta el dashboard táctico de su "
                "propio departamento"
            )

    # ============================================================ US3: verificación operativa
    async def verificacion_operativos(self) -> dict:
        publicacion = await self.repo.ultima_publicacion_operativa()
        if publicacion is None:
            raise NotFoundError(
                "Todavía no se ha ejecutado la verificación de dashboards operativos"
            )
        estados = await self.repo.estado_operativo(publicacion.publicacion_id)
        return {
            "publicacion_id": publicacion.publicacion_id,
            "fecha_verificacion": publicacion.fecha_hora,
            "estado_por_tienda": estados,
        }

    async def alertas_operativos(self) -> dict:
        publicacion = await self.repo.ultima_publicacion_operativa()
        if publicacion is None:
            raise NotFoundError(
                "Todavía no se ha ejecutado la verificación de dashboards operativos"
            )
        estados = await self.repo.estado_operativo(
            publicacion.publicacion_id, solo_no_disponibles=True
        )
        return {
            "publicacion_id": publicacion.publicacion_id,
            "fecha_verificacion": publicacion.fecha_hora,
            "estado_por_tienda": estados,
        }
