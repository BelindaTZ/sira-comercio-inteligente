"""Orquestación de una corrida de carga de UNA entidad del modelo (feature 010,
US2/US3), en tres pasos ELT (Principio III):

    paso_extract   Extract (PostgreSQL) → Load raw (MinIO `landing-zone`)
    paso_load      Load (ClickHouse) + las 2 reglas de calidad
    paso_transform Transform in-warehouse (`OPTIMIZE ... FINAL`) → cierra la corrida

El DAG `carga_diaria_warehouse` los expone como tres tasks encadenados por
entidad (el `landing-zone` es el hand-off entre `extract` y `load`). El endpoint
de desarrollo `POST /plataforma-datos/corridas/forzar` los compone en una sola
llamada (`correr_carga`), en una única transacción.

Reglas transversales:
  - La fila `corrida_carga` se abre en `paso_extract` (estado `en_progreso`). El
    índice único parcial `uq_corrida_carga_en_progreso` rechaza una segunda
    corrida sobre la misma entidad (FR-005) → `CorridaEnProgresoError`.
  - `desde` (punto de corte incremental) = `fecha_fin` de la última corrida
    **exitosa** de esa entidad, o `None` = carga completa (FR-003).
  - Cualquier paso que falle marca la corrida `fallida` y re-lanza (FR-004: se
    puede reprocesar sin duplicar — `ReplacingMergeTree`).
  - Todo el estado es un registro real en PostgreSQL (Principio II), nunca se
    lee de los logs de Airflow (SC-004).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from . import (
    extract_postgres,
    load_clickhouse,
    load_landing_zone_minio,
    transform_in_warehouse,
)

_BUCKET_LANDING_DEFAULT = "landing-zone"


class CorridaEnProgresoError(RuntimeError):
    """Ya hay una corrida 'en_progreso' para esa entidad (FR-005)."""


@dataclass
class ExtractResult:
    corrida_id: int
    tipo_carga: str  # 'completa' | 'incremental'
    filas_extraidas: int
    landing_key: str | None = None
    filas: list[dict] = field(default_factory=list)  # en memoria (path in-process)


@dataclass
class LoadResult:
    filas_cargadas: int
    filas_error: int


@dataclass
class ResultadoCorrida:
    corrida_id: int
    estado: str
    tipo_carga: str
    filas_cargadas: int
    filas_error: int
    landing_key: str | None = None


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _marcar_fallida(session, corrida_id: int) -> None:
    await session.execute(
        text(
            "UPDATE corrida_carga SET estado = 'fallida', fecha_fin = CURRENT_TIMESTAMP "
            "WHERE corrida_id = :id AND estado = 'en_progreso'"
        ),
        {"id": corrida_id},
    )
    await session.flush()


async def _abrir_corrida(session, entidad_id: int, tipo_carga: str, origen: str) -> int:
    # SAVEPOINT: si el índice único parcial rechaza la 2ª corrida (FR-005), sólo se
    # revierte este INSERT, no la transacción entera.
    try:
        async with session.begin_nested():
            corrida_id = await session.scalar(
                text("""
                    INSERT INTO corrida_carga (entidad_id, tipo_carga, origen, estado)
                    VALUES (:e, :t, :o, 'en_progreso')
                    RETURNING corrida_id
                """),
                {"e": entidad_id, "t": tipo_carga, "o": origen},
            )
        return corrida_id
    except IntegrityError as exc:
        raise CorridaEnProgresoError(
            f"Ya hay una corrida en progreso para la entidad {entidad_id}"
        ) from exc


# ============================================================ paso 1: EXTRACT
async def paso_extract(
    session,
    *,
    entidad_id: int,
    nombre_entidad: str,
    tipo_carga_forzado: str | None = None,
    cliente_minio=None,
    bucket_landing: str = _BUCKET_LANDING_DEFAULT,
) -> ExtractResult:
    """Abre la corrida, extrae de PostgreSQL y deja el raw en `landing-zone`."""
    ultima_fin = await session.scalar(
        text("""
            SELECT fecha_fin FROM corrida_carga
            WHERE entidad_id = :e AND estado = 'exitosa'
            ORDER BY fecha_fin DESC LIMIT 1
        """),
        {"e": entidad_id},
    )
    desde = None if tipo_carga_forzado == "completa" else ultima_fin
    tipo_carga = "completa" if desde is None else "incremental"

    corrida_id = await _abrir_corrida(session, entidad_id, tipo_carga, "postgres")

    try:
        extraido = await extract_postgres.extraer(session, nombre_entidad, desde)
        filas = extraido.rows
        landing_key = None
        if cliente_minio is not None:
            landing_key = load_landing_zone_minio.volcar(
                cliente_minio,
                bucket=bucket_landing,
                nombre_entidad=nombre_entidad,
                corrida_id=corrida_id,
                fecha_inicio=_ahora(),
                rows=filas,
            )
        return ExtractResult(
            corrida_id=corrida_id,
            tipo_carga=tipo_carga,
            filas_extraidas=len(filas),
            landing_key=landing_key,
            filas=filas,
        )
    except Exception:
        await _marcar_fallida(session, corrida_id)
        raise


# ============================================================ paso 2: LOAD
async def paso_load(
    session,
    *,
    corrida_id: int,
    nombre_entidad: str,
    filas: list[dict] | None = None,
    cliente_minio=None,
    bucket_landing: str = _BUCKET_LANDING_DEFAULT,
    landing_key: str | None = None,
    cliente_ch=None,
    claves_validas: dict[str, set] | None = None,
) -> LoadResult:
    """Carga a ClickHouse + reglas de calidad. Toma las filas de memoria (`filas`)
    o, si no las tiene, las relee del `landing-zone` (hand-off del DAG)."""
    try:
        if filas is None:
            if landing_key is None or cliente_minio is None:
                raise ValueError(
                    "paso_load necesita `filas` o (`cliente_minio` + `landing_key`)"
                )
            filas = load_landing_zone_minio.leer(
                cliente_minio, bucket=bucket_landing, key=landing_key
            )

        problemas: list[tuple[str, str | None]] = []

        if cliente_ch is not None:
            carga = load_clickhouse.cargar(
                cliente_ch,
                nombre_entidad=nombre_entidad,
                filas=filas,
                claves_validas=claves_validas,
                on_issue=lambda desc, ident: problemas.append((desc, ident)),
            )
            filas_cargadas, filas_error = carga.filas_cargadas, carga.filas_error
        else:
            filas_cargadas, filas_error = len(filas), 0

        for desc, ident in problemas:
            await session.execute(
                text("""
                    INSERT INTO registro_calidad_carga
                        (corrida_id, descripcion_problema, identificador_registro)
                    VALUES (:c, :d, :i)
                """),
                {"c": corrida_id, "d": desc[:300], "i": ident},
            )
        await session.execute(
            text(
                "UPDATE corrida_carga SET filas_cargadas = :fc, filas_error = :fe "
                "WHERE corrida_id = :id"
            ),
            {"fc": filas_cargadas, "fe": filas_error, "id": corrida_id},
        )
        await session.flush()
        return LoadResult(filas_cargadas=filas_cargadas, filas_error=filas_error)
    except Exception:
        await _marcar_fallida(session, corrida_id)
        raise


# ============================================================ paso 3: TRANSFORM
async def paso_transform(
    session, *, corrida_id: int, nombre_entidad: str, cliente_ch=None
) -> str:
    """Transformación in-warehouse y cierre de la corrida como `exitosa`.

    `fecha_fin` la fija el reloj de la BD (CURRENT_TIMESTAMP), el mismo que marca
    `fecha_hora`/`updated_at` en las tablas origen — así el punto de corte
    incremental (research.md Decisión 3) compara relojes homogéneos.
    """
    try:
        if cliente_ch is not None:
            transform_in_warehouse.transformar(
                cliente_ch, nombre_entidad=nombre_entidad
            )
        await session.execute(
            text("""
                UPDATE corrida_carga
                SET estado = 'exitosa', fecha_fin = CURRENT_TIMESTAMP,
                    filas_cargadas = COALESCE(filas_cargadas, 0)
                WHERE corrida_id = :id
            """),
            {"id": corrida_id},
        )
        await session.flush()
        return "exitosa"
    except Exception:
        await _marcar_fallida(session, corrida_id)
        raise


# ============================================================ composición (dev / tests)
async def correr_carga(
    session,
    *,
    entidad_id: int,
    nombre_entidad: str,
    tipo_carga_forzado: str | None = None,
    cliente_minio=None,
    bucket_landing: str = _BUCKET_LANDING_DEFAULT,
    cliente_ch=None,
    claves_validas: dict[str, set] | None = None,
) -> ResultadoCorrida:
    """Los tres pasos en una sola transacción — lo usa el endpoint dev de forzar
    corrida y los tests. `session` hace commit por fuera."""
    ex = await paso_extract(
        session,
        entidad_id=entidad_id,
        nombre_entidad=nombre_entidad,
        tipo_carga_forzado=tipo_carga_forzado,
        cliente_minio=cliente_minio,
        bucket_landing=bucket_landing,
    )
    ld = await paso_load(
        session,
        corrida_id=ex.corrida_id,
        nombre_entidad=nombre_entidad,
        filas=ex.filas,
        cliente_ch=cliente_ch,
        claves_validas=claves_validas,
    )
    await paso_transform(
        session,
        corrida_id=ex.corrida_id,
        nombre_entidad=nombre_entidad,
        cliente_ch=cliente_ch,
    )
    return ResultadoCorrida(
        corrida_id=ex.corrida_id,
        estado="exitosa",
        tipo_carga=ex.tipo_carga,
        filas_cargadas=ld.filas_cargadas,
        filas_error=ld.filas_error,
        landing_key=ex.landing_key,
    )
