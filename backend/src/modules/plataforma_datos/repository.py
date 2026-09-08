"""PlataformaDatosRepository — acceso a datos de las 4 tablas de control del
pipeline ELT (feature 010). Sin lógica de negocio (Principio XI).

Los datos de negocio del warehouse (fact_venta + dimensiones) NO se tocan aquí:
viven en ClickHouse y sólo los escriben los jobs de `data_platform/` (Principio III).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.corrida_carga import CorridaCarga
from src.models.modelo_datos_warehouse import ModeloDatosWarehouse
from src.models.politica_gobierno_datos import PoliticaGobiernoDatos
from src.models.registro_calidad_carga import RegistroCalidadCarga


class PlataformaDatosRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def agregar(self, entity) -> None:
        self.session.add(entity)

    async def flush(self) -> None:
        await self.session.flush()

    # ------------------------------------------------------------ modelo (US1)
    async def listar_modelo(self) -> list[ModeloDatosWarehouse]:
        stmt = select(ModeloDatosWarehouse).order_by(ModeloDatosWarehouse.entidad_id)
        return list((await self.session.scalars(stmt)).all())

    async def get_entidad(self, entidad_id: int) -> ModeloDatosWarehouse | None:
        return await self.session.get(ModeloDatosWarehouse, entidad_id)

    async def get_entidad_por_nombre(self, nombre: str) -> ModeloDatosWarehouse | None:
        stmt = select(ModeloDatosWarehouse).where(
            ModeloDatosWarehouse.nombre_entidad == nombre
        )
        return (await self.session.scalars(stmt)).first()

    async def crear_entidad(
        self, entidad: ModeloDatosWarehouse
    ) -> ModeloDatosWarehouse:
        self.session.add(entidad)
        await self.session.flush()
        await self.session.refresh(entidad)
        return entidad

    async def entidades_activas(self) -> list[ModeloDatosWarehouse]:
        stmt = (
            select(ModeloDatosWarehouse)
            .where(ModeloDatosWarehouse.activa.is_(True))
            .order_by(ModeloDatosWarehouse.entidad_id)
        )
        return list((await self.session.scalars(stmt)).all())

    # ------------------------------------------------------------ corridas (US2/US3)
    async def listar_corridas(
        self, *, entidad_id: int | None = None, estado: str | None = None
    ) -> list[dict]:
        """Devuelve cada corrida con el nombre de su entidad y la duración derivada
        (`fecha_fin - fecha_inicio`, data-model.md — no se persiste)."""
        rows = await self.session.execute(
            text("""
                SELECT c.corrida_id, c.entidad_id, m.nombre_entidad,
                       c.tipo_carga, c.origen, c.estado,
                       c.filas_cargadas, c.filas_error,
                       c.fecha_inicio, c.fecha_fin,
                       CASE WHEN c.fecha_fin IS NOT NULL
                            THEN CAST(EXTRACT(EPOCH FROM (c.fecha_fin - c.fecha_inicio)) AS INTEGER)
                       END AS duracion_segundos
                FROM corrida_carga c
                JOIN modelo_datos_warehouse m ON m.entidad_id = c.entidad_id
                WHERE (CAST(:entidad_id AS INTEGER) IS NULL OR c.entidad_id = :entidad_id)
                  AND (CAST(:estado AS TEXT) IS NULL OR c.estado = :estado)
                ORDER BY c.fecha_inicio DESC, c.corrida_id DESC
            """),
            {"entidad_id": entidad_id, "estado": estado},
        )
        return [dict(r._mapping) for r in rows]

    async def get_corrida(self, corrida_id: int) -> CorridaCarga | None:
        return await self.session.get(CorridaCarga, corrida_id)

    async def corrida_en_progreso(self, entidad_id: int) -> CorridaCarga | None:
        stmt = select(CorridaCarga).where(
            CorridaCarga.entidad_id == entidad_id,
            CorridaCarga.estado == "en_progreso",
        )
        return (await self.session.scalars(stmt)).first()

    async def ultima_corrida_exitosa(self, entidad_id: int) -> CorridaCarga | None:
        stmt = (
            select(CorridaCarga)
            .where(
                CorridaCarga.entidad_id == entidad_id,
                CorridaCarga.estado == "exitosa",
            )
            .order_by(CorridaCarga.fecha_fin.desc())
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def abrir_corrida(
        self, *, entidad_id: int, tipo_carga: str, origen: str
    ) -> CorridaCarga:
        corrida = CorridaCarga(
            entidad_id=entidad_id,
            tipo_carga=tipo_carga,
            origen=origen,
            estado="en_progreso",
        )
        self.session.add(corrida)
        await self.session.flush()
        await self.session.refresh(corrida)
        return corrida

    async def cerrar_corrida(
        self,
        corrida: CorridaCarga,
        *,
        estado: str,
        filas_cargadas: int | None,
        filas_error: int,
        fecha_fin: datetime,
    ) -> None:
        corrida.estado = estado
        corrida.filas_cargadas = filas_cargadas
        corrida.filas_error = filas_error
        corrida.fecha_fin = fecha_fin
        await self.session.flush()

    # ------------------------------------------------------------ calidad (US3)
    async def registrar_calidad(
        self, *, corrida_id: int, descripcion: str, identificador: str | None
    ) -> RegistroCalidadCarga:
        fila = RegistroCalidadCarga(
            corrida_id=corrida_id,
            descripcion_problema=descripcion,
            identificador_registro=identificador,
        )
        self.session.add(fila)
        await self.session.flush()
        return fila

    async def registros_calidad(self, corrida_id: int) -> list[RegistroCalidadCarga]:
        stmt = (
            select(RegistroCalidadCarga)
            .where(RegistroCalidadCarga.corrida_id == corrida_id)
            .order_by(RegistroCalidadCarga.fecha_hora, RegistroCalidadCarga.registro_id)
        )
        return list((await self.session.scalars(stmt)).all())

    # ------------------------------------------------------------ política (US4)
    async def politica_vigente(self) -> PoliticaGobiernoDatos | None:
        stmt = (
            select(PoliticaGobiernoDatos)
            .order_by(
                PoliticaGobiernoDatos.fecha_creacion.desc(),
                PoliticaGobiernoDatos.politica_id.desc(),
            )
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def politica_historial(self) -> list[PoliticaGobiernoDatos]:
        stmt = select(PoliticaGobiernoDatos).order_by(
            PoliticaGobiernoDatos.fecha_creacion.desc(),
            PoliticaGobiernoDatos.politica_id.desc(),
        )
        return list((await self.session.scalars(stmt)).all())

    async def crear_politica(
        self, politica: PoliticaGobiernoDatos
    ) -> PoliticaGobiernoDatos:
        self.session.add(politica)
        await self.session.flush()
        await self.session.refresh(politica)
        return politica
