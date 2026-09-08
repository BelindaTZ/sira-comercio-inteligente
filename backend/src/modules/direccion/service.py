"""DireccionService — regla de lectura del dashboard estratégico consolidado
(feature 009, US1, OO-7.4.1).

No recalcula ningún KPI (Principio VIII): devuelve el último snapshot que publicó
el job diario (`jobs/publicar_dashboard_estrategico.py`). Si aún no hay ninguna
publicación exitosa, es un 404 — no se inventa un dashboard vacío.
"""

from __future__ import annotations

from src.modules.direccion.repository import DireccionRepository
from src.shared.exceptions import NotFoundError


class DireccionService:
    def __init__(self, repo: DireccionRepository) -> None:
        self.repo = repo

    async def dashboard_estrategico(self) -> dict:
        publicacion = await self.repo.ultima_publicacion_exitosa()
        if publicacion is None:
            raise NotFoundError("Todavía no se ha publicado ningún dashboard estratégico")
        return {
            "publicacion_id": publicacion.publicacion_id,
            "fecha_publicacion": publicacion.fecha_hora,
            "kpis": await self.repo.kpis_de(publicacion.publicacion_id),
        }
