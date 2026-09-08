"""Orquestación de una corrida de carga de UNA entidad del modelo (feature 010,
US2/US3). Lo usan tanto el DAG de Airflow (`carga_diaria_warehouse`) como el
endpoint de desarrollo `POST /plataforma-datos/corridas/forzar`.

Flujo (research.md Decisiones 2/3/4, Principio III):
  1. Abrir la fila `corrida_carga` en 'en_progreso'. El índice único parcial
     `uq_corrida_carga_en_progreso` rechaza una segunda corrida sobre la misma
     entidad (FR-005) — se traduce a `CorridaEnProgresoError`.
  2. `desde` = fecha de fin de la última corrida **exitosa** (incremental) o
     `None` (completa / primera corrida, FR-003).
  3. Extract (PostgreSQL) → Load raw (MinIO landing-zone) → Load (ClickHouse, con
     las 2 reglas de calidad) → Transform in-warehouse.
  4. Cerrar la corrida ('exitosa' con filas_cargadas/filas_error, o 'fallida').

Todo el estado es un registro real en PostgreSQL (Principio II) — nunca se
consulta el estado de una corrida desde los logs de Airflow (SC-004).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from . import (
    extract_postgres,
    load_clickhouse,
    load_landing_zone_minio,
    transform_in_warehouse,
)


class CorridaEnProgresoError(RuntimeError):
    """Ya hay una corrida 'en_progreso' para esa entidad (FR-005)."""


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


async def correr_carga(
    session,
    *,
    entidad_id: int,
    nombre_entidad: str,
    tipo_carga_forzado: str | None = None,
    cliente_minio=None,
    bucket_landing: str = "landing-zone",
    cliente_ch=None,
    claves_validas: dict[str, set] | None = None,
) -> ResultadoCorrida:
    """`cliente_minio` / `cliente_ch` None → se omite ese paso (modo mock/dev sin
    warehouse configurado). `session` debe hacer commit por fuera."""
    # --- 2. punto de corte incremental ---
    ultima_fin = await session.scalar(
        text("""
            SELECT fecha_fin FROM corrida_carga
            WHERE entidad_id = :e AND estado = 'exitosa'
            ORDER BY fecha_fin DESC LIMIT 1
        """),
        {"e": entidad_id},
    )
    if tipo_carga_forzado == "completa":
        desde = None
    elif tipo_carga_forzado == "incremental":
        desde = ultima_fin
    else:
        desde = ultima_fin  # sin forzar: completa si nunca hubo una exitosa

    tipo_carga = "completa" if desde is None else "incremental"

    # --- 1. abrir corrida (exclusión mutua vía índice único parcial) ---
    corrida_id = await _abrir_corrida(session, entidad_id, tipo_carga, "postgres")

    landing_key: str | None = None
    try:
        # --- 3a. Extract ---
        extraido = await extract_postgres.extraer(session, nombre_entidad, desde)
        filas = extraido.rows

        # --- 3b. Load raw → MinIO landing-zone ---
        if cliente_minio is not None:
            landing_key = load_landing_zone_minio.volcar(
                cliente_minio,
                bucket=bucket_landing,
                nombre_entidad=nombre_entidad,
                corrida_id=corrida_id,
                fecha_inicio=_ahora(),
                rows=filas,
            )

        # --- 3c. Load → ClickHouse + reglas de calidad ---
        problemas: list[tuple[str, str | None]] = []

        def _sink(desc: str, ident: str | None) -> None:
            problemas.append((desc, ident))

        if cliente_ch is not None:
            carga = load_clickhouse.cargar(
                cliente_ch,
                nombre_entidad=nombre_entidad,
                filas=filas,
                claves_validas=claves_validas,
                on_issue=_sink,
            )
            filas_cargadas, filas_error = carga.filas_cargadas, carga.filas_error
            # --- 3d. Transform in-warehouse ---
            transform_in_warehouse.transformar(
                cliente_ch, nombre_entidad=nombre_entidad
            )
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

        # --- 4. cerrar corrida OK ---
        # fecha_fin la fija el reloj de la BD (CURRENT_TIMESTAMP), el mismo que
        # marca `fecha_hora`/`updated_at` en las tablas origen — así el punto de
        # corte incremental (research.md Decisión 3) compara relojes homogéneos.
        await session.execute(
            text("""
                UPDATE corrida_carga
                SET estado = 'exitosa', filas_cargadas = :fc, filas_error = :fe,
                    fecha_fin = CURRENT_TIMESTAMP
                WHERE corrida_id = :id
            """),
            {"fc": filas_cargadas, "fe": filas_error, "id": corrida_id},
        )
        await session.flush()
        return ResultadoCorrida(
            corrida_id=corrida_id,
            estado="exitosa",
            tipo_carga=tipo_carga,
            filas_cargadas=filas_cargadas,
            filas_error=filas_error,
            landing_key=landing_key,
        )
    except Exception:
        await session.execute(
            text(
                "UPDATE corrida_carga SET estado = 'fallida', fecha_fin = CURRENT_TIMESTAMP "
                "WHERE corrida_id = :id"
            ),
            {"id": corrida_id},
        )
        await session.flush()
        raise
