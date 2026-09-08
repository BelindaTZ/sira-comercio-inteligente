"""Integration tests — pipeline ELT de la Plataforma de Datos (feature 010).

Los más críticos de la feature (tasks.md): idempotencia del reproceso (T021) y
exclusión mutua por destino (T022). Se ejercita `dags_utils.pipeline` directo
contra el PostgreSQL real (origen + control), con dobles en memoria para MinIO
`landing-zone` y ClickHouse — el contrato de idempotencia/exclusión no depende
del volumen de producción (quickstart.md).
"""

from __future__ import annotations

from collections import defaultdict

import pytest
from dags_utils import pipeline
from sqlalchemy import text

pytestmark = pytest.mark.asyncio

# clave natural (ORDER BY del ReplacingMergeTree, schema_warehouse.sql)
_ORDER_KEY = {
    "fact_venta": ("venta_detalle_id",),
    "dim_cliente": ("household_id",),
    "dim_producto": ("product_id",),
    "dim_tienda": ("tienda_id",),
    "dim_caja": ("caja_id",),
    "dim_empleado": ("empleado_id",),
}


class FakeClickHouse:
    """Simula `ReplacingMergeTree`: última escritura por clave natural gana, así
    reprocesar la misma ventana no duplica filas (FR-004)."""

    def __init__(self) -> None:
        self.tablas: dict[str, dict[tuple, dict]] = defaultdict(dict)
        self.fallar_en_insert = False

    def insert(self, tabla: str, filas: list[dict]) -> None:
        if self.fallar_en_insert:
            raise RuntimeError("ClickHouse caído a mitad de la corrida")
        cols = _ORDER_KEY[tabla]
        for f in filas:
            self.tablas[tabla][tuple(f[c] for c in cols)] = f

    def command(self, sql: str) -> None:  # OPTIMIZE ... FINAL
        pass

    def filas(self, tabla: str) -> list[dict]:
        return list(self.tablas[tabla].values())


class _FakeObj:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def close(self) -> None:
        pass

    def release_conn(self) -> None:
        pass


class FakeMinio:
    def __init__(self) -> None:
        self.objetos: dict[str, bytes] = {}

    def put_object(self, bucket, key, data, length, content_type=None):  # noqa: ARG002
        self.objetos[f"{bucket}/{key}"] = data.read()

    def get_object(self, bucket, key):
        return _FakeObj(self.objetos[f"{bucket}/{key}"])


async def _entidad_id(session, nombre: str) -> int:
    return await session.scalar(
        text("SELECT entidad_id FROM modelo_datos_warehouse WHERE nombre_entidad = :n"),
        {"n": nombre},
    )


# ------------------------------------------------------------------ T019: carga base
async def test_carga_base_completa_trae_historico(db_session, escenario_plataforma_datos):
    s = db_session
    ent = escenario_plataforma_datos["entidad_fact"]
    ch, minio = FakeClickHouse(), FakeMinio()

    res = await pipeline.correr_carga(
        s,
        entidad_id=ent,
        nombre_entidad="fact_venta",
        tipo_carga_forzado="completa",
        cliente_minio=minio,
        cliente_ch=ch,
    )
    assert res.estado == "exitosa"
    assert res.tipo_carga == "completa"
    assert res.filas_cargadas == len(ch.filas("fact_venta")) > 0
    assert minio.objetos, "el raw del Extract debe quedar en landing-zone"


# ------------------------------------------------------------------ T020: incremental
async def test_incremental_solo_trae_filas_nuevas(db_session, escenario_plataforma_datos):
    s = db_session
    e = escenario_plataforma_datos
    ent = e["entidad_fact"]
    ch = FakeClickHouse()

    await pipeline.correr_carga(
        s,
        entidad_id=ent,
        nombre_entidad="fact_venta",
        tipo_carga_forzado="completa",
        cliente_ch=ch,
    )
    base = len(ch.filas("fact_venta"))

    # una venta nueva posterior a la corrida exitosa
    venta_id = await s.scalar(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
            "VALUES (:t, :c, CURRENT_TIMESTAMP, 20, 0, 'confirmada') RETURNING venta_id"
        ),
        {"t": e["tienda_id"], "c": e["cajero_id"]},
    )
    await s.execute(
        text(
            "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
            "VALUES (:v, :p, 3, 7.50)"
        ),
        {"v": venta_id, "p": e["product_id"]},
    )
    await s.flush()

    res = await pipeline.correr_carga(
        s,
        entidad_id=ent,
        nombre_entidad="fact_venta",
        tipo_carga_forzado="incremental",
        cliente_ch=ch,
    )
    assert res.tipo_carga == "incremental"
    assert res.filas_cargadas == 1  # sólo el detalle nuevo
    assert len(ch.filas("fact_venta")) == base + 1


# ------------------------------------------------------------------ T021: idempotencia
async def test_reprocesar_no_duplica(db_session, escenario_plataforma_datos):
    s = db_session
    ent = escenario_plataforma_datos["entidad_fact"]
    ch = FakeClickHouse()

    await pipeline.correr_carga(
        s,
        entidad_id=ent,
        nombre_entidad="fact_venta",
        tipo_carga_forzado="completa",
        cliente_ch=ch,
    )
    tras_primera = len(ch.filas("fact_venta"))

    # reproceso de la misma ventana (otra completa) — ReplacingMergeTree dedup
    await pipeline.correr_carga(
        s,
        entidad_id=ent,
        nombre_entidad="fact_venta",
        tipo_carga_forzado="completa",
        cliente_ch=ch,
    )
    assert len(ch.filas("fact_venta")) == tras_primera


# ------------------------------------------------------------------ T022: exclusión mutua
async def test_dos_corridas_en_progreso_rechazadas(db_session, escenario_plataforma_datos):
    s = db_session
    ent = escenario_plataforma_datos["entidad_tienda"]

    # deja una corrida abierta 'en_progreso' a mano
    await s.execute(
        text(
            "INSERT INTO corrida_carga (entidad_id, tipo_carga, origen, estado) "
            "VALUES (:e, 'incremental', 'postgres', 'en_progreso')"
        ),
        {"e": ent},
    )
    await s.flush()

    with pytest.raises(pipeline.CorridaEnProgresoError):
        await pipeline.correr_carga(
            s,
            entidad_id=ent,
            nombre_entidad="dim_tienda",
            tipo_carga_forzado="completa",
            cliente_ch=FakeClickHouse(),
        )


# ------------------------------------------------------------------ T021b: corrida fallida a medias
async def test_corrida_fallida_queda_registrada(db_session, escenario_plataforma_datos):
    s = db_session
    ent = escenario_plataforma_datos["entidad_fact"]
    ch = FakeClickHouse()
    ch.fallar_en_insert = True

    with pytest.raises(RuntimeError):
        await pipeline.correr_carga(
            s,
            entidad_id=ent,
            nombre_entidad="fact_venta",
            tipo_carga_forzado="completa",
            cliente_ch=ch,
        )
    estado = await s.scalar(
        text(
            "SELECT estado FROM corrida_carga WHERE entidad_id = :e "
            "ORDER BY corrida_id DESC LIMIT 1"
        ),
        {"e": ent},
    )
    assert estado == "fallida"


# ------------------------------------------------------------------ T015 (US1): entidad inactiva
async def test_entidad_inactiva_no_se_carga_desde_el_dag(db_session, escenario_plataforma_datos):
    s = db_session
    ent = escenario_plataforma_datos["entidad_producto"]
    await s.execute(
        text("UPDATE modelo_datos_warehouse SET activa = false WHERE entidad_id = :e"),
        {"e": ent},
    )
    await s.flush()

    activas = await s.execute(
        text("SELECT nombre_entidad FROM modelo_datos_warehouse WHERE activa = true")
    )
    nombres = {r[0] for r in activas}
    assert "dim_producto" not in nombres  # el DAG no genera task para ella


# ------------------------------------------------------------------ T030/T032 (US3): calidad
async def test_referencia_rota_se_senala_sin_frenar_el_lote(db_session, escenario_plataforma_datos):
    s = db_session
    e = escenario_plataforma_datos
    ent = e["entidad_fact"]
    ch = FakeClickHouse()

    todos = {r[0] for r in await s.execute(text("SELECT product_id FROM productos"))}
    tiendas = {r[0] for r in await s.execute(text("SELECT tienda_id FROM tiendas"))}

    # carga base limpia (fija el punto de corte incremental)
    await pipeline.correr_carga(
        s,
        entidad_id=ent,
        nombre_entidad="fact_venta",
        tipo_carga_forzado="completa",
        cliente_ch=ch,
        claves_validas={"dim_producto": todos, "dim_tienda": tiendas},
    )

    # una venta nueva con dos líneas: el producto principal y `product_cold`.
    venta_id = await s.scalar(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
            "VALUES (:t, :c, CURRENT_TIMESTAMP, 21, 0, 'confirmada') RETURNING venta_id"
        ),
        {"t": e["tienda_id"], "c": e["cajero_id"]},
    )
    await s.execute(
        text(
            "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
            "VALUES (:v, :p, 1, 2.00), (:v, :p2, 1, 2.00)"
        ),
        {"v": venta_id, "p": e["product_id"], "p2": e["product_cold"]},
    )
    await s.flush()

    # `product_cold` aún no está en dim_producto del warehouse (la carga de la
    # dimensión va por detrás) → su fila de fact queda con la referencia rota.
    res = await pipeline.correr_carga(
        s,
        entidad_id=ent,
        nombre_entidad="fact_venta",
        tipo_carga_forzado="incremental",
        cliente_ch=ch,
        claves_validas={
            "dim_producto": todos - {e["product_cold"]},
            "dim_tienda": tiendas,
        },
    )
    assert res.tipo_carga == "incremental"
    assert res.filas_error == 1
    assert res.filas_cargadas == 1
    registros = await s.execute(
        text("SELECT descripcion_problema FROM registro_calidad_carga WHERE corrida_id = :c"),
        {"c": res.corrida_id},
    )
    descripciones = [r[0] for r in registros]
    assert any("referencia rota" in d for d in descripciones)


# --------------------------------------------------- pasos ELT como tasks separados (DAG)
async def test_pasos_elt_encadenados_via_landing_zone(db_session, escenario_plataforma_datos):
    """extract -> load -> transform como los ejecuta el DAG: `load` NO recibe las
    filas en memoria, las relee del `landing-zone` (el hand-off real del ELT)."""
    s = db_session
    ent = escenario_plataforma_datos["entidad_tienda"]
    ch, minio = FakeClickHouse(), FakeMinio()

    ex = await pipeline.paso_extract(
        s,
        entidad_id=ent,
        nombre_entidad="dim_tienda",
        tipo_carga_forzado="completa",
        cliente_minio=minio,
    )
    assert ex.landing_key and f"landing-zone/{ex.landing_key}" in minio.objetos

    estado_tras_extract = await s.scalar(
        text("SELECT estado FROM corrida_carga WHERE corrida_id = :c"), {"c": ex.corrida_id}
    )
    assert estado_tras_extract == "en_progreso"  # la corrida sigue abierta entre tasks

    ld = await pipeline.paso_load(
        s,
        corrida_id=ex.corrida_id,
        nombre_entidad="dim_tienda",
        cliente_minio=minio,
        landing_key=ex.landing_key,
        cliente_ch=ch,
    )
    assert ld.filas_cargadas == len(ch.filas("dim_tienda")) > 0

    estado = await pipeline.paso_transform(
        s, corrida_id=ex.corrida_id, nombre_entidad="dim_tienda", cliente_ch=ch
    )
    assert estado == "exitosa"
    fila = (
        await s.execute(
            text("SELECT estado, filas_cargadas FROM corrida_carga WHERE corrida_id = :c"),
            {"c": ex.corrida_id},
        )
    ).one()
    assert fila.estado == "exitosa" and fila.filas_cargadas == ld.filas_cargadas


async def test_fallo_en_load_marca_la_corrida_fallida(db_session, escenario_plataforma_datos):
    s = db_session
    ent = escenario_plataforma_datos["entidad_tienda"]
    ch = FakeClickHouse()
    ch.fallar_en_insert = True

    ex = await pipeline.paso_extract(
        s,
        entidad_id=ent,
        nombre_entidad="dim_tienda",
        tipo_carga_forzado="completa",
    )
    with pytest.raises(RuntimeError):
        await pipeline.paso_load(
            s,
            corrida_id=ex.corrida_id,
            nombre_entidad="dim_tienda",
            filas=ex.filas,
            cliente_ch=ch,
        )
    estado = await s.scalar(
        text("SELECT estado FROM corrida_carga WHERE corrida_id = :c"), {"c": ex.corrida_id}
    )
    assert estado == "fallida"
