"""PlataformaDatosService — regla de negocio del control del pipeline ELT
(feature 010, OT-7.1 / OO-7.5.1).

No mueve datos de negocio: eso ocurre en `data_platform/` (DAGs de Airflow,
Principio III). Este servicio gobierna el catálogo del modelo (US1), expone la
trazabilidad de cada corrida (US2/US3), mantiene la política de gobierno de datos
(US4, append-only) y —sólo fuera de producción— fuerza una corrida manual (FR-012)
reutilizando el mismo orquestador que el DAG (`dags_utils.pipeline`).
"""

from __future__ import annotations

import sys
from pathlib import Path

from src.models.modelo_datos_warehouse import ModeloDatosWarehouse
from src.models.politica_gobierno_datos import PoliticaGobiernoDatos
from src.modules.plataforma_datos.repository import PlataformaDatosRepository
from src.modules.plataforma_datos.schemas import EntidadModeloCreate, EntidadModeloPatch
from src.shared.exceptions import BusinessRuleError, ConflictError, NotFoundError

# `data_platform/dags` en el path: el orquestador ELT es compartido con el DAG
# (una sola implementación de la corrida, research.md Decisiones 2/3).
_DATA_PLATFORM = Path(__file__).resolve().parents[4] / "data_platform" / "dags"
if _DATA_PLATFORM.is_dir() and str(_DATA_PLATFORM) not in sys.path:
    sys.path.insert(0, str(_DATA_PLATFORM))


class PlataformaDatosService:
    def __init__(self, repo: PlataformaDatosRepository) -> None:
        self.repo = repo

    # ============================================================ US1: modelo
    async def listar_modelo(self) -> list[ModeloDatosWarehouse]:
        return await self.repo.listar_modelo()

    async def registrar_entidad(
        self, data: EntidadModeloCreate, *, empleado_id: int
    ) -> ModeloDatosWarehouse:
        if await self.repo.get_entidad_por_nombre(data.nombre_entidad) is not None:
            raise ConflictError(
                f"La entidad '{data.nombre_entidad}' ya está en el modelo"
            )
        return await self.repo.crear_entidad(
            ModeloDatosWarehouse(
                nombre_entidad=data.nombre_entidad,
                tipo=data.tipo,
                tabla_origen_postgres=data.tabla_origen_postgres,
                descripcion=data.descripcion,
                activa=True,
                definido_por=empleado_id,
            )
        )

    async def actualizar_entidad(
        self, entidad_id: int, data: EntidadModeloPatch
    ) -> ModeloDatosWarehouse:
        entidad = await self.repo.get_entidad(entidad_id)
        if entidad is None:
            raise NotFoundError(f"Entidad {entidad_id} no existe en el modelo")
        if data.activa is not None:
            entidad.activa = data.activa
        if data.descripcion is not None:
            entidad.descripcion = data.descripcion
        await self.repo.flush()
        return entidad

    # ============================================================ US2/US3: corridas
    async def listar_corridas(
        self, *, entidad_id: int | None, estado: str | None
    ) -> list[dict]:
        return await self.repo.listar_corridas(entidad_id=entidad_id, estado=estado)

    async def calidad_de_corrida(self, corrida_id: int) -> dict:
        if await self.repo.get_corrida(corrida_id) is None:
            raise NotFoundError(f"Corrida {corrida_id} no existe")
        return {
            "corrida_id": corrida_id,
            "registros": await self.repo.registros_calidad(corrida_id),
        }

    # ============================================================ US4: política
    async def politica_vigente(self) -> PoliticaGobiernoDatos:
        vigente = await self.repo.politica_vigente()
        if vigente is None:
            raise NotFoundError(
                "Aún no se registró ninguna política de gobierno de datos"
            )
        return vigente

    async def politica_historial(self) -> list[PoliticaGobiernoDatos]:
        return await self.repo.politica_historial()

    async def registrar_politica(
        self, texto: str, *, empleado_id: int
    ) -> PoliticaGobiernoDatos:
        return await self.repo.crear_politica(
            PoliticaGobiernoDatos(texto=texto, definido_por=empleado_id)
        )

    # ============================================================ FR-012: forzar corrida (dev)
    async def forzar_corrida(self, entidad_id: int, tipo_carga: str) -> dict:
        entidad = await self.repo.get_entidad(entidad_id)
        if entidad is None:
            raise NotFoundError(f"Entidad {entidad_id} no existe en el modelo")
        if not entidad.activa:
            raise BusinessRuleError(
                f"La entidad '{entidad.nombre_entidad}' está inactiva — actívala antes de cargar"
            )

        from dags_utils import pipeline  # import perezoso (dev only)

        try:
            res = await pipeline.correr_carga(
                self.repo.session,
                entidad_id=entidad_id,
                nombre_entidad=entidad.nombre_entidad,
                tipo_carga_forzado=tipo_carga,
                cliente_minio=None,
                cliente_ch=None,  # sin warehouse configurado: corrida de control, sin mover datos
            )
        except pipeline.CorridaEnProgresoError as exc:
            raise ConflictError(str(exc)) from exc
        return {"corrida_id": res.corrida_id, "estado": res.estado}
