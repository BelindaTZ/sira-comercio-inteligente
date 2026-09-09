"""Fixtures compartidas de pytest (async).

Los tests de contrato/integración corren contra la BD PostgreSQL real vía Docker
(research.md #3), no con mocks. Cada test corre dentro de una transacción que se
revierte al final (aislamiento por savepoint), así no ensucian la base.

Requisitos: `docker compose up -d postgres`, la BD `sira_test` creada y migrada:

    docker exec sira-postgres psql -U sira -d postgres -c "CREATE DATABASE sira_test"
    TEST_DATABASE_URL= DATABASE_URL=postgresql+asyncpg://sira:sira@127.0.0.1:15432/sira_test \
        .venv/Scripts/python -m alembic upgrade head

Los tests corren SIEMPRE contra `settings.test_db_url` (`<db>_test` por defecto, o
`TEST_DATABASE_URL` si se define) — aislada del dataset de demo que
`scripts/cargar_dataset_inicial` carga en `DATABASE_URL`.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import date, timedelta
from decimal import Decimal

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from src.core.config import settings
from src.core.database import get_session
from src.main import app

if "WindowsSelectorEventLoopPolicy" in dir(asyncio):  # pragma: no cover - Windows + asyncpg
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # Engine propio con NullPool: cada test abre y cierra su conexión real y no
    # deja conexiones en pool ligadas a un event loop ya cerrado (pytest-asyncio
    # crea un loop por test).
    test_engine = create_async_engine(settings.test_db_url, poolclass=NullPool)
    conn = await test_engine.connect()
    trans = await conn.begin()
    session_factory = async_sessionmaker(
        bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await conn.close()
        await test_engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_session, None)


async def _mk_empleado(session: AsyncSession, tienda_id: int | None = None) -> int:
    """Crea un empleado dedicado (con su propio puesto) para un token de prueba."""
    puesto_id = await session.scalar(
        text(
            "INSERT INTO roles_puesto (nombre) VALUES "
            "('Puesto ' || gen_random_uuid()::text) RETURNING puesto_id"
        )
    )
    return await session.scalar(
        text(
            "INSERT INTO empleados (tienda_id, puesto_id, nombre, fecha_contratacion) "
            "VALUES (:t, :p, 'Actor Test', CURRENT_DATE) RETURNING empleado_id"
        ),
        {"t": tienda_id, "p": puesto_id},
    )


async def _token(
    session: AsyncSession,
    *,
    role_id: int,
    empleado_id: int | None = None,
    tienda_id: int | None = None,
    activo: bool = True,
    rol: str | None = None,  # aceptado por compatibilidad, el rol se resuelve de la BD
) -> str:
    """Feature 008: el JWT sólo transporta `usuario_id`. Crea (o actualiza) la
    cuenta `usuarios` real y devuelve un token que el backend resuelve contra la BD."""
    import uuid

    if empleado_id is None:
        empleado_id = await _mk_empleado(session, tienda_id)
    usuario_id = await session.scalar(
        text(
            "INSERT INTO usuarios (empleado_id, role_id, username, password_hash, activo) "
            "VALUES (:e, :r, :u, 'x', :a) "
            "ON CONFLICT (empleado_id) DO UPDATE SET role_id = EXCLUDED.role_id, "
            "activo = EXCLUDED.activo RETURNING usuario_id"
        ),
        {
            "e": empleado_id,
            "r": role_id,
            "u": f"u{empleado_id}-{uuid.uuid4().hex[:8]}",
            "a": activo,
        },
    )
    await session.flush()
    return jwt.encode(
        {"usuario_id": usuario_id}, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )


@pytest_asyncio.fixture
async def escenario_pos(db_session: AsyncSession) -> dict:
    """Crea el mínimo dato real para operar el POS: tienda, cajero, encargado,
    medios de pago, un producto con precio, inventario y dos lotes con distinta
    fecha de vencimiento (para probar FEFO)."""
    s = db_session

    role_cajero = await s.scalar(text("SELECT role_id FROM roles WHERE nombre = 'Cajero'"))
    role_encargado = await s.scalar(
        text("SELECT role_id FROM roles WHERE nombre = 'Encargado_Tienda'")
    )

    puesto_id = await s.scalar(
        text(
            "INSERT INTO roles_puesto (nombre) VALUES ('Puesto test "
            "' || gen_random_uuid()::text) RETURNING puesto_id"
        )
    )
    tienda_id = await s.scalar(
        text(
            "INSERT INTO tiendas (codigo, nombre) VALUES "
            "(substr(md5(random()::text), 1, 8), 'Tienda Test') RETURNING tienda_id"
        )
    )
    cajero_id = await s.scalar(
        text(
            "INSERT INTO empleados (tienda_id, puesto_id, nombre, fecha_contratacion) "
            "VALUES (:t, :p, 'Cajero Test', CURRENT_DATE) RETURNING empleado_id"
        ),
        {"t": tienda_id, "p": puesto_id},
    )
    encargado_id = await s.scalar(
        text(
            "INSERT INTO empleados (tienda_id, puesto_id, nombre, fecha_contratacion) "
            "VALUES (:t, :p, 'Encargado Test', CURRENT_DATE) RETURNING empleado_id"
        ),
        {"t": tienda_id, "p": puesto_id},
    )

    mp_efectivo = await s.scalar(
        text(
            "INSERT INTO medios_pago (nombre) VALUES ('Efectivo') "
            "ON CONFLICT (nombre) DO UPDATE SET nombre = EXCLUDED.nombre RETURNING medio_pago_id"
        )
    )
    mp_tarjeta = await s.scalar(
        text(
            "INSERT INTO medios_pago (nombre) VALUES ('Tarjeta') "
            "ON CONFLICT (nombre) DO UPDATE SET nombre = EXCLUDED.nombre RETURNING medio_pago_id"
        )
    )

    product_id = await s.scalar(text("SELECT COALESCE(MAX(product_id), 0) + 1 FROM productos"))
    await s.execute(
        text(
            "INSERT INTO productos (product_id, product_category, product_type, "
            "costo, precio_base, es_perecedero, codigo_barras) "
            "VALUES (:pid, 'TEST CAT', 'TEST PROD', 1.00, :precio, true, :barcode)"
        ),
        {"pid": product_id, "precio": Decimal("2.50"), "barcode": f"BC{product_id}"},
    )

    await s.execute(
        text(
            "INSERT INTO inventario (product_id, tienda_id, cantidad_disponible) "
            "VALUES (:pid, :tid, 100)"
        ),
        {"pid": product_id, "tid": tienda_id},
    )
    # Lote A vence antes → debe salir primero (FEFO).
    lote_a = await s.scalar(
        text(
            "INSERT INTO lotes (product_id, tienda_id, cantidad_recibida, cantidad_disponible, "
            "fecha_vencimiento) VALUES (:pid, :tid, 40, 40, :fv) RETURNING lote_id"
        ),
        {"pid": product_id, "tid": tienda_id, "fv": date.today() + timedelta(days=5)},
    )
    lote_b = await s.scalar(
        text(
            "INSERT INTO lotes (product_id, tienda_id, cantidad_recibida, cantidad_disponible, "
            "fecha_vencimiento) VALUES (:pid, :tid, 60, 60, :fv) RETURNING lote_id"
        ),
        {"pid": product_id, "tid": tienda_id, "fv": date.today() + timedelta(days=30)},
    )
    await s.flush()

    return {
        "tienda_id": tienda_id,
        "cajero_id": cajero_id,
        "encargado_id": encargado_id,
        "product_id": product_id,
        "codigo_barras": f"BC{product_id}",
        "precio_base": Decimal("2.50"),
        "medio_efectivo": mp_efectivo,
        "medio_tarjeta": mp_tarjeta,
        "lote_a": lote_a,
        "lote_b": lote_b,
        "token_cajero": await _token(
            s, empleado_id=cajero_id, role_id=role_cajero, tienda_id=tienda_id
        ),
        "token_encargado": await _token(
            s, empleado_id=encargado_id, role_id=role_encargado, tienda_id=tienda_id
        ),
    }


@pytest.fixture
def auth_cajero(escenario_pos: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_pos['token_cajero']}"}


@pytest.fixture
def auth_encargado(escenario_pos: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_pos['token_encargado']}"}


@pytest_asyncio.fixture
async def escenario_forecasting(db_session: AsyncSession, escenario_pos: dict) -> dict:
    """Amplía `escenario_pos` para la feature 004: un Jefe_TI y un Jefe_Operaciones
    con token, ~16 semanas de ventas confirmadas del producto principal (historial
    suficiente) y un segundo producto con sólo 3 semanas (cold start)."""
    from datetime import datetime

    s = db_session
    e = escenario_pos
    anio = 2025

    async def _rol(nombre: str) -> int:
        return await s.scalar(text("SELECT role_id FROM roles WHERE nombre = :n"), {"n": nombre})

    rol_ti = await _rol("Jefe_TI")
    rol_ops = await _rol("Jefe_Operaciones")

    # producto cold start en la misma tienda
    cold_id = await s.scalar(text("SELECT COALESCE(MAX(product_id),0)+1 FROM productos"))
    await s.execute(
        text(
            "INSERT INTO productos (product_id, product_category, product_type, costo, "
            "precio_base, es_perecedero) VALUES (:p, 'TEST CAT', 'COLD', 1.00, 3.00, false)"
        ),
        {"p": cold_id},
    )

    async def _semana_de_ventas(product_id: int, semana: int, unidades: int) -> None:
        venta_id = await s.scalar(
            text(
                "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
                "VALUES (:t, :c, :f, :sem, 0, 'confirmada') RETURNING venta_id"
            ),
            {
                "t": e["tienda_id"],
                "c": e["cajero_id"],
                "f": datetime(anio, 1, 1) + timedelta(weeks=semana - 1),
                "sem": semana,
            },
        )
        await s.execute(
            text(
                "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
                "VALUES (:v, :p, :cant, 2.50)"
            ),
            {"v": venta_id, "p": product_id, "cant": unidades},
        )

    for semana in range(1, 17):
        # patrón semanal estable + leve tendencia → el modelo aprende bien
        await _semana_de_ventas(e["product_id"], semana, 10 + (semana % 4))
    for semana in range(1, 4):
        await _semana_de_ventas(cold_id, semana, 5)
    await s.flush()

    return {
        **e,
        "anio_historial": anio,
        "product_cold": cold_id,
        "semana_pronostico": 17,  # primera semana del horizonte tras 16 semanas
        "token_jefe_ti": await _token(s, role_id=rol_ti, tienda_id=e["tienda_id"]),
        "token_jefe_ops": await _token(s, role_id=rol_ops, tienda_id=e["tienda_id"]),
    }


@pytest.fixture
def auth_jefe_ti(escenario_forecasting: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_forecasting['token_jefe_ti']}"}


@pytest.fixture
def auth_jefe_ops_fc(escenario_forecasting: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_forecasting['token_jefe_ops']}"}


@pytest_asyncio.fixture
async def escenario_promociones(db_session: AsyncSession, escenario_pos: dict) -> dict:
    """Amplía `escenario_pos` para la feature 005: productos A/B con afinidad fuerte
    (comprados juntos en casi todos los tickets) + un producto C de baja rotación,
    un cliente con consentimiento, y tokens de Jefe_Marketing / Jefe_Operaciones."""
    from datetime import UTC, datetime

    s = db_session
    e = escenario_pos
    prod_a = e["product_id"]

    async def _rol(nombre: str) -> int:
        return await s.scalar(text("SELECT role_id FROM roles WHERE nombre = :n"), {"n": nombre})

    rol_mkt = await _rol("Jefe_Marketing")
    rol_ops = await _rol("Jefe_Operaciones")

    async def _producto(cat: str, tipo: str) -> int:
        pid = await s.scalar(text("SELECT COALESCE(MAX(product_id),0)+1 FROM productos"))
        await s.execute(
            text(
                "INSERT INTO productos (product_id, product_category, product_type, costo, "
                "precio_base, activo) VALUES (:p, :c, :t, 1.00, 3.00, true)"
            ),
            {"p": pid, "c": cat, "t": tipo},
        )
        return pid

    prod_b = await _producto("TEST CAT", "AFIN B")
    prod_c = await _producto("CAT BAJA", "ROTACION BAJA")
    # productos de relleno para que el Pareto de "CAT BAJA" deje a C fuera de A/B
    prod_top = await _producto("CAT BAJA", "TOP")

    household_id = await s.scalar(
        text(
            "INSERT INTO clientes (nombre, email, consentimiento_datos, activo) "
            "VALUES ('Cliente Afin', 'afin@test.local', true, true) RETURNING household_id"
        )
    )

    async def _venta(productos: list[int], household=None, semana=1) -> int:
        venta_id = await s.scalar(
            text(
                "INSERT INTO ventas (tienda_id, cajero_id, household_id, fecha_hora, semana, "
                "total, estado) VALUES (:t, :c, :h, :f, :sem, 0, 'confirmada') RETURNING venta_id"
            ),
            {
                "t": e["tienda_id"],
                "c": e["cajero_id"],
                "h": household,
                "f": datetime.now(UTC).replace(tzinfo=None),
                "sem": semana,
            },
        )
        for p in productos:
            await s.execute(
                text(
                    "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
                    "VALUES (:v, :p, 1, 3.00)"
                ),
                {"v": venta_id, "p": p},
            )
        return venta_id

    # afinidad fuerte A↔B: 12 tickets con ambos, 2 con solo A, 1 con solo B
    for _ in range(12):
        await _venta([prod_a, prod_b])
    for _ in range(2):
        await _venta([prod_a])
    await _venta([prod_b])
    # producto TOP concentra el valor de 'CAT BAJA'; C casi no vende
    for _ in range(20):
        await _venta([prod_top])
    await _venta([prod_c])  # una sola venta histórica de C

    # inventario de C en la tienda (para candidatos a liquidación)
    await s.execute(
        text(
            "INSERT INTO inventario (product_id, tienda_id, cantidad_disponible) "
            "VALUES (:p, :t, 50)"
        ),
        {"p": prod_c, "t": e["tienda_id"]},
    )
    await s.flush()

    return {
        **e,
        "product_a": prod_a,
        "product_b": prod_b,
        "product_c": prod_c,
        "household_afin": household_id,
        "token_jefe_marketing": await _token(s, role_id=rol_mkt, tienda_id=e["tienda_id"]),
        "token_jefe_ops": await _token(s, role_id=rol_ops, tienda_id=e["tienda_id"]),
    }


@pytest.fixture
def auth_mkt(escenario_promociones: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_promociones['token_jefe_marketing']}"}


@pytest.fixture
def auth_ops(escenario_promociones: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_promociones['token_jefe_ops']}"}


@pytest_asyncio.fixture
async def auth_jefe_comercial(db_session: AsyncSession, escenario_pos: dict) -> dict[str, str]:
    role_id = await db_session.scalar(
        text("SELECT role_id FROM roles WHERE nombre = 'Jefe_Comercial'")
    )
    token = await _token(db_session, role_id=role_id, tienda_id=escenario_pos["tienda_id"])
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def escenario_pricing(db_session: AsyncSession, escenario_pos: dict) -> dict:
    """Amplía `escenario_pos` para la feature 003: usuarios reales (para resolver
    el rol de quien autoriza un descuento, research.md §4), un Jefe_Comercial y un
    Jefe_TI (rol NO habilitado para autorizar descuentos)."""
    s = db_session
    e = escenario_pos
    tienda_id = e["tienda_id"]

    async def _rol(nombre: str) -> int:
        return await s.scalar(text("SELECT role_id FROM roles WHERE nombre = :n"), {"n": nombre})

    async def _empleado(nombre: str) -> int:
        puesto_id = await s.scalar(
            text(
                "INSERT INTO roles_puesto (nombre) VALUES "
                "('Puesto ' || gen_random_uuid()::text) RETURNING puesto_id"
            )
        )
        return await s.scalar(
            text(
                "INSERT INTO empleados (tienda_id, puesto_id, nombre, fecha_contratacion) "
                "VALUES (:t, :p, :n, CURRENT_DATE) RETURNING empleado_id"
            ),
            {"t": tienda_id, "p": puesto_id, "n": nombre},
        )

    rol_jefe_comercial = await _rol("Jefe_Comercial")
    rol_jefe_ti = await _rol("Jefe_TI")

    jefe_comercial_id = await _empleado("Jefe Comercial Test")
    jefe_ti_id = await _empleado("Jefe TI Test")
    await s.flush()

    return {
        **e,
        "jefe_comercial_id": jefe_comercial_id,
        "jefe_ti_id": jefe_ti_id,
        "token_jefe_comercial": await _token(
            s, empleado_id=jefe_comercial_id, role_id=rol_jefe_comercial, tienda_id=tienda_id
        ),
        "token_jefe_ti": await _token(
            s, empleado_id=jefe_ti_id, role_id=rol_jefe_ti, tienda_id=tienda_id
        ),
    }


@pytest.fixture
def auth_pricing_jc(escenario_pricing: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_pricing['token_jefe_comercial']}"}


@pytest_asyncio.fixture
async def auth_jefe_marketing(db_session: AsyncSession, escenario_pos: dict) -> dict[str, str]:
    role_id = await db_session.scalar(
        text("SELECT role_id FROM roles WHERE nombre = 'Jefe_Marketing'")
    )
    token = await _token(db_session, role_id=role_id, tienda_id=escenario_pos["tienda_id"])
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def escenario_inventario(db_session: AsyncSession, escenario_pos: dict) -> dict:
    """Amplía `escenario_pos` con lo que necesita US2: un Reponedor, un proveedor,
    una orden de compra `aprobada` y un producto SIN stock previo."""
    s = db_session
    tienda_id = escenario_pos["tienda_id"]

    role_reponedor = await s.scalar(text("SELECT role_id FROM roles WHERE nombre = 'Reponedor'"))
    puesto_id = await s.scalar(
        text(
            "INSERT INTO roles_puesto (nombre) VALUES "
            "('Puesto rep ' || gen_random_uuid()::text) RETURNING puesto_id"
        )
    )
    reponedor_id = await s.scalar(
        text(
            "INSERT INTO empleados (tienda_id, puesto_id, nombre, fecha_contratacion) "
            "VALUES (:t, :p, 'Reponedor Test', CURRENT_DATE) RETURNING empleado_id"
        ),
        {"t": tienda_id, "p": puesto_id},
    )
    proveedor_id = await s.scalar(
        text("INSERT INTO proveedores (nombre) VALUES ('Proveedor Test') RETURNING proveedor_id")
    )
    orden_id = await s.scalar(
        text(
            "INSERT INTO ordenes_compra (proveedor_id, tienda_id, empleado_id, estado) "
            "VALUES (:pr, :t, :e, 'aprobada') RETURNING orden_id"
        ),
        {"pr": proveedor_id, "t": tienda_id, "e": escenario_pos["encargado_id"]},
    )
    # Producto nuevo, sin inventario ni lotes todavía.
    product_id = await s.scalar(text("SELECT COALESCE(MAX(product_id), 0) + 1 FROM productos"))
    await s.execute(
        text(
            "INSERT INTO productos (product_id, product_category, product_type, costo, "
            "precio_base, es_perecedero) VALUES (:pid, 'CAT US2', 'PROD US2', 1.20, 3.00, true)"
        ),
        {"pid": product_id},
    )
    await s.execute(
        text(
            "INSERT INTO orden_compra_detalle (orden_id, product_id, cantidad, costo_unitario) "
            "VALUES (:o, :p, 100, 1.20)"
        ),
        {"o": orden_id, "p": product_id},
    )
    await s.flush()

    return {
        **escenario_pos,
        "reponedor_id": reponedor_id,
        "proveedor_id": proveedor_id,
        "orden_id": orden_id,
        "product_us2": product_id,
        "token_reponedor": await _token(
            s, empleado_id=reponedor_id, role_id=role_reponedor, tienda_id=tienda_id
        ),
    }


@pytest.fixture
def auth_reponedor(escenario_inventario: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_inventario['token_reponedor']}"}


@pytest_asyncio.fixture
async def escenario_compras(db_session: AsyncSession, escenario_inventario: dict) -> dict:
    """Amplía `escenario_inventario` con los jefes que operan compras y finanzas."""
    s = db_session
    tienda_id = escenario_inventario["tienda_id"]

    role_jefe_ops = await s.scalar(
        text("SELECT role_id FROM roles WHERE nombre = 'Jefe_Operaciones'")
    )
    role_jefe_fin = await s.scalar(text("SELECT role_id FROM roles WHERE nombre = 'Jefe_Finanzas'"))
    puesto_id = await s.scalar(
        text(
            "INSERT INTO roles_puesto (nombre) VALUES "
            "('Puesto jefe ' || gen_random_uuid()::text) RETURNING puesto_id"
        )
    )
    jefe_ops_id = await s.scalar(
        text(
            "INSERT INTO empleados (tienda_id, puesto_id, nombre, fecha_contratacion) "
            "VALUES (:t, :p, 'Jefe Ops Test', CURRENT_DATE) RETURNING empleado_id"
        ),
        {"t": tienda_id, "p": puesto_id},
    )
    jefe_fin_id = await s.scalar(
        text(
            "INSERT INTO empleados (tienda_id, puesto_id, nombre, fecha_contratacion) "
            "VALUES (:t, :p, 'Jefe Fin Test', CURRENT_DATE) RETURNING empleado_id"
        ),
        {"t": tienda_id, "p": puesto_id},
    )
    await s.flush()

    return {
        **escenario_inventario,
        "jefe_ops_id": jefe_ops_id,
        "jefe_fin_id": jefe_fin_id,
        "token_jefe_ops": await _token(
            s, empleado_id=jefe_ops_id, role_id=role_jefe_ops, tienda_id=tienda_id
        ),
        "token_jefe_fin": await _token(
            s, empleado_id=jefe_fin_id, role_id=role_jefe_fin, tienda_id=tienda_id
        ),
    }


@pytest.fixture
def auth_jefe_ops(escenario_compras: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_compras['token_jefe_ops']}"}


@pytest.fixture
def auth_jefe_fin(escenario_compras: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_compras['token_jefe_fin']}"}


@pytest_asyncio.fixture
async def escenario_caja(db_session: AsyncSession, escenario_pos: dict) -> dict:
    """Amplía `escenario_pos` para la feature 006: dos cajas de la tienda con un
    datáfono cada una (uno con firmware desactualizado), y tokens de Jefe_Finanzas,
    Jefe_TI y Jefe_Operaciones. Reutiliza el cajero/encargado de `escenario_pos`."""
    s = db_session
    e = escenario_pos

    async def _rol(nombre: str) -> int:
        return await s.scalar(text("SELECT role_id FROM roles WHERE nombre = :n"), {"n": nombre})

    rol_fin = await _rol("Jefe_Finanzas")
    rol_ti = await _rol("Jefe_TI")
    rol_ops = await _rol("Jefe_Operaciones")

    caja_1 = await s.scalar(
        text("INSERT INTO cajas (tienda_id, nombre) VALUES (:t, 'Caja 1') RETURNING caja_id"),
        {"t": e["tienda_id"]},
    )
    caja_2 = await s.scalar(
        text("INSERT INTO cajas (tienda_id, nombre) VALUES (:t, 'Caja 2') RETURNING caja_id"),
        {"t": e["tienda_id"]},
    )
    datafono_viejo = await s.scalar(
        text(
            "INSERT INTO datafonos (caja_id, modelo, version_firmware, estado) "
            "VALUES (:c, 'Verifone VX', '2.9.0', 'activo') RETURNING datafono_id"
        ),
        {"c": caja_1},
    )
    datafono_nuevo = await s.scalar(
        text(
            "INSERT INTO datafonos (caja_id, modelo, version_firmware, estado) "
            "VALUES (:c, 'Ingenico Move', '3.2.0', 'activo') RETURNING datafono_id"
        ),
        {"c": caja_2},
    )
    await s.flush()

    jefe_finanzas_id = await _mk_empleado(s, e["tienda_id"])
    jefe_ti_id = await _mk_empleado(s, e["tienda_id"])
    jefe_ops_id = await _mk_empleado(s, e["tienda_id"])

    return {
        **e,
        "caja_1": caja_1,
        "caja_2": caja_2,
        "datafono_viejo": datafono_viejo,
        "datafono_nuevo": datafono_nuevo,
        "jefe_finanzas_id": jefe_finanzas_id,
        "jefe_ti_id": jefe_ti_id,
        "jefe_ops_id": jefe_ops_id,
        "token_jefe_finanzas": await _token(
            s, empleado_id=jefe_finanzas_id, role_id=rol_fin, tienda_id=e["tienda_id"]
        ),
        "token_jefe_ti": await _token(
            s, empleado_id=jefe_ti_id, role_id=rol_ti, tienda_id=e["tienda_id"]
        ),
        "token_jefe_operaciones": await _token(
            s, empleado_id=jefe_ops_id, role_id=rol_ops, tienda_id=e["tienda_id"]
        ),
    }


@pytest.fixture
def auth_caja_finanzas(escenario_caja: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_caja['token_jefe_finanzas']}"}


@pytest.fixture
def auth_caja_ti(escenario_caja: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_caja['token_jefe_ti']}"}


@pytest.fixture
def auth_caja_ops(escenario_caja: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_caja['token_jefe_operaciones']}"}


@pytest_asyncio.fixture
async def escenario_pagos(db_session: AsyncSession, escenario_caja: dict) -> dict:
    """Amplía `escenario_caja` para la feature 007: un estándar de seguridad de
    pagos vigente (firmware ≥ 3.0.0 — deja `datafono_viejo` no conforme y
    `datafono_nuevo` conforme), una política de seguridad vigente, y un token de
    Jefe_Comercial (reporte mensual de tiempo de cobro)."""
    s = db_session
    e = escenario_caja

    rol_comercial = await s.scalar(
        text("SELECT role_id FROM roles WHERE nombre = 'Jefe_Comercial'")
    )
    await s.execute(
        text(
            "INSERT INTO configuracion_seguridad_pagos (version_minima_firmware, actualizado_por) "
            "VALUES ('3.0.0', :emp)"
        ),
        {"emp": e["encargado_id"]},
    )
    await s.execute(
        text(
            "INSERT INTO politica_seguridad_pagos (texto, definido_por) "
            "VALUES ('Política inicial de prueba', :emp)"
        ),
        {"emp": e["encargado_id"]},
    )
    await s.flush()

    return {
        **e,
        "token_jefe_comercial": await _token(s, role_id=rol_comercial, tienda_id=e["tienda_id"]),
    }


@pytest.fixture
def auth_pagos_comercial(escenario_pagos: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_pagos['token_jefe_comercial']}"}


@pytest_asyncio.fixture
async def escenario_auth(db_session: AsyncSession) -> dict:
    """Feature 008: cuentas reales con contraseña bcrypt conocida para probar el
    login. Un Jefe_TI (administra Sistema), un Jefe_RRHH (empleados) y un Cajero
    corriente."""
    from src.shared.passwords import hash_password

    s = db_session

    async def _rol(nombre: str) -> int:
        return await s.scalar(text("SELECT role_id FROM roles WHERE nombre = :n"), {"n": nombre})

    tienda_id = await s.scalar(
        text(
            "INSERT INTO tiendas (codigo, nombre) VALUES "
            "(substr(md5(random()::text), 1, 8), 'Tienda Auth') RETURNING tienda_id"
        )
    )
    puesto_id = await s.scalar(
        text(
            "INSERT INTO roles_puesto (nombre) VALUES ('P-'||gen_random_uuid()) RETURNING puesto_id"
        )
    )

    async def _cuenta(nombre_rol: str, username: str, password: str) -> dict:
        emp = await s.scalar(
            text(
                "INSERT INTO empleados (tienda_id, puesto_id, nombre, email, fecha_contratacion) "
                "VALUES (:t, :p, :n, :em, CURRENT_DATE) RETURNING empleado_id"
            ),
            {"t": tienda_id, "p": puesto_id, "n": username, "em": f"{username}@sira.test"},
        )
        uid = await s.scalar(
            text(
                "INSERT INTO usuarios (empleado_id, role_id, username, password_hash) "
                "VALUES (:e, :r, :u, :h) RETURNING usuario_id"
            ),
            {"e": emp, "r": await _rol(nombre_rol), "u": username, "h": hash_password(password)},
        )
        token = jwt.encode(
            {"usuario_id": uid}, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        return {
            "empleado_id": emp,
            "usuario_id": uid,
            "username": username,
            "password": password,
            "email": f"{username}@sira.test",
            "token": token,
        }

    await s.flush()
    ti = await _cuenta("Jefe_TI", "jefe.ti", "Password-TI-2026")
    rrhh = await _cuenta("Jefe_RRHH", "jefe.rrhh", "Password-RRHH-2026")
    cajero = await _cuenta("Cajero", "cajero.uno", "Password-Cajero-2026")
    encargado = await _cuenta("Encargado_Tienda", "encargado.uno", "Password-Enc-2026")
    await s.flush()

    return {
        "tienda_id": tienda_id,
        "puesto_id": puesto_id,
        "rol_cajero_id": await _rol("Cajero"),
        "rol_encargado_id": await _rol("Encargado_Tienda"),
        "ti": ti,
        "rrhh": rrhh,
        "cajero": cajero,
        "encargado": encargado,
    }


@pytest.fixture
def auth_admin_ti(escenario_auth: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_auth['ti']['token']}"}


@pytest.fixture
def auth_rrhh(escenario_auth: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_auth['rrhh']['token']}"}


@pytest_asyncio.fixture
async def escenario_rrhh(db_session: AsyncSession) -> dict:
    """Feature 011: dos tiendas, un Jefe_RRHH (sin tienda), un Encargado de la
    tienda A, un puesto crítico y uno normal, y cuatro empleados-cajero: dos con
    cuenta activa en la tienda A, uno sin cuenta en la tienda A, y uno con cuenta
    en la tienda B (para probar el fan-out por rol y la restricción por tienda)."""
    s = db_session

    async def _rol(nombre: str) -> int:
        return await s.scalar(text("SELECT role_id FROM roles WHERE nombre = :n"), {"n": nombre})

    rol_rrhh = await _rol("Jefe_RRHH")
    rol_encargado = await _rol("Encargado_Tienda")
    rol_cajero = await _rol("Cajero")

    async def _tienda(nombre: str) -> int:
        return await s.scalar(
            text(
                "INSERT INTO tiendas (codigo, nombre) VALUES "
                "(substr(md5(random()::text), 1, 8), :n) RETURNING tienda_id"
            ),
            {"n": nombre},
        )

    async def _puesto(prefijo: str, critico: bool) -> int:
        return await s.scalar(
            text(
                "INSERT INTO roles_puesto (nombre, es_critico) VALUES "
                "(:p || '-' || gen_random_uuid()::text, :c) RETURNING puesto_id"
            ),
            {"p": prefijo, "c": critico},
        )

    async def _empleado(tienda_id: int, puesto_id: int, nombre: str) -> int:
        return await s.scalar(
            text(
                "INSERT INTO empleados (tienda_id, puesto_id, nombre, fecha_contratacion) "
                "VALUES (:t, :p, :n, DATE '2026-01-01') RETURNING empleado_id"
            ),
            {"t": tienda_id, "p": puesto_id, "n": nombre},
        )

    tienda_a = await _tienda("Tienda RRHH A")
    tienda_b = await _tienda("Tienda RRHH B")
    puesto_critico = await _puesto("Puesto critico", True)
    puesto_normal = await _puesto("Puesto normal", False)

    cajero_a1 = await _empleado(tienda_a, puesto_normal, "Cajero A1")
    cajero_a2 = await _empleado(tienda_a, puesto_normal, "Cajero A2")
    cajero_a_sin_cuenta = await _empleado(tienda_a, puesto_normal, "Cajero A sin cuenta")
    cajero_b1 = await _empleado(tienda_b, puesto_normal, "Cajero B1")
    empleado_critico_a = await _empleado(tienda_a, puesto_critico, "Encargada A")
    await s.flush()

    token_rrhh = await _token(s, role_id=rol_rrhh)
    token_encargado_a = await _token(
        s,
        empleado_id=await _empleado(tienda_a, puesto_normal, "Encargado token A"),
        role_id=rol_encargado,
        tienda_id=tienda_a,
    )
    token_encargado_b = await _token(
        s,
        empleado_id=await _empleado(tienda_b, puesto_normal, "Encargado token B"),
        role_id=rol_encargado,
        tienda_id=tienda_b,
    )
    # cuentas de cajero: A1 y A2 con cuenta, B1 con cuenta; A sin cuenta se deja sin usuario.
    await _token(s, empleado_id=cajero_a1, role_id=rol_cajero, tienda_id=tienda_a)
    await _token(s, empleado_id=cajero_a2, role_id=rol_cajero, tienda_id=tienda_a)
    await _token(s, empleado_id=cajero_b1, role_id=rol_cajero, tienda_id=tienda_b)
    await s.flush()

    return {
        "tienda_a": tienda_a,
        "tienda_b": tienda_b,
        "rol_cajero_id": rol_cajero,
        "puesto_critico_id": puesto_critico,
        "puesto_normal_id": puesto_normal,
        "cajero_a1": cajero_a1,
        "cajero_a2": cajero_a2,
        "cajero_a_sin_cuenta": cajero_a_sin_cuenta,
        "cajero_b1": cajero_b1,
        "empleado_critico_a": empleado_critico_a,
        "token_rrhh": token_rrhh,
        "token_encargado_a": token_encargado_a,
        "token_encargado_b": token_encargado_b,
    }


@pytest.fixture
def auth_jefe_rrhh(escenario_rrhh: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_rrhh['token_rrhh']}"}


@pytest.fixture
def auth_encargado_rrhh(escenario_rrhh: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_rrhh['token_encargado_a']}"}


@pytest_asyncio.fixture
async def escenario_traslados(db_session: AsyncSession) -> dict:
    """Feature 012: dos tiendas, un Jefe_Operaciones (toda la red), un Encargado
    por tienda, y un producto perecedero con inventario + lote en ambas tiendas
    (tienda A con exceso; tienda B por debajo de su punto de reposición para
    probar la sugerencia de compra extendida)."""
    s = db_session

    async def _rol(nombre: str) -> int:
        return await s.scalar(text("SELECT role_id FROM roles WHERE nombre = :n"), {"n": nombre})

    rol_ops = await _rol("Jefe_Operaciones")
    rol_encargado = await _rol("Encargado_Tienda")

    async def _tienda(nombre: str) -> int:
        return await s.scalar(
            text(
                "INSERT INTO tiendas (codigo, nombre) VALUES "
                "(substr(md5(random()::text), 1, 8), :n) RETURNING tienda_id"
            ),
            {"n": nombre},
        )

    tienda_a = await _tienda("Traslados A")
    tienda_b = await _tienda("Traslados B")

    product_id = await s.scalar(text("SELECT COALESCE(MAX(product_id), 0) + 1 FROM productos"))
    await s.execute(
        text(
            "INSERT INTO productos (product_id, product_category, product_type, costo, "
            "precio_base, es_perecedero, codigo_barras) "
            "VALUES (:pid, 'CAT TRASLADO', 'PROD TRASLADO', 2.00, 5.00, true, :bc)"
        ),
        {"pid": product_id, "bc": f"BCT{product_id}"},
    )
    venc = date.today() + timedelta(days=20)

    async def _stock(tienda_id: int, cantidad: int, minima: int) -> None:
        await s.execute(
            text(
                "INSERT INTO inventario (product_id, tienda_id, cantidad_disponible, "
                "cantidad_minima) VALUES (:p, :t, :c, :m)"
            ),
            {"p": product_id, "t": tienda_id, "c": cantidad, "m": minima},
        )
        await s.execute(
            text(
                "INSERT INTO lotes (product_id, tienda_id, cantidad_recibida, cantidad_disponible, "
                "fecha_vencimiento) VALUES (:p, :t, :c, :c, :fv)"
            ),
            {"p": product_id, "t": tienda_id, "c": cantidad, "fv": venc},
        )

    await _stock(tienda_a, cantidad=200, minima=0)
    await _stock(tienda_b, cantidad=10, minima=50)

    enc_a = await _mk_empleado(s, tienda_a)
    enc_b = await _mk_empleado(s, tienda_b)
    await s.flush()

    return {
        "tienda_a": tienda_a,
        "tienda_b": tienda_b,
        "product_id": product_id,
        "fecha_vencimiento": venc.isoformat(),
        "encargado_a_id": enc_a,
        "encargado_b_id": enc_b,
        "token_ops": await _token(s, role_id=rol_ops, tienda_id=tienda_a),
        "token_encargado_a": await _token(
            s, empleado_id=enc_a, role_id=rol_encargado, tienda_id=tienda_a
        ),
        "token_encargado_b": await _token(
            s, empleado_id=enc_b, role_id=rol_encargado, tienda_id=tienda_b
        ),
    }


@pytest.fixture
def auth_traslados_ops(escenario_traslados: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_traslados['token_ops']}"}


@pytest_asyncio.fixture
async def escenario_plataforma_datos(
    db_session: AsyncSession, escenario_forecasting: dict
) -> dict:
    """Feature 010: reutiliza el historial de ventas + el Jefe_TI de
    `escenario_forecasting` y siembra el catálogo `modelo_datos_warehouse` con
    `fact_venta` + `dim_producto` + `dim_tienda` activas (para las corridas de
    US2/US3). El resto de dimensiones las registran los tests de US1."""
    s = db_session
    e = escenario_forecasting

    jefe_ti_emp = await _mk_empleado(s, e["tienda_id"])
    rol_ti = await s.scalar(text("SELECT role_id FROM roles WHERE nombre = 'Jefe_TI'"))
    token_ti = await _token(s, empleado_id=jefe_ti_emp, role_id=rol_ti, tienda_id=e["tienda_id"])

    async def _entidad(nombre: str, tipo: str, origen: str) -> int:
        return await s.scalar(
            text(
                "INSERT INTO modelo_datos_warehouse "
                "(nombre_entidad, tipo, tabla_origen_postgres, definido_por) "
                "VALUES (:n, :t, :o, :d) RETURNING entidad_id"
            ),
            {"n": nombre, "t": tipo, "o": origen, "d": jefe_ti_emp},
        )

    entidad_fact = await _entidad("fact_venta", "fact", "venta_detalle")
    entidad_producto = await _entidad("dim_producto", "dimension", "productos")
    entidad_tienda = await _entidad("dim_tienda", "dimension", "tiendas")
    await s.flush()

    return {
        **e,
        "jefe_ti_emp": jefe_ti_emp,
        "token_ti": token_ti,
        "entidad_fact": entidad_fact,
        "entidad_producto": entidad_producto,
        "entidad_tienda": entidad_tienda,
    }


@pytest.fixture
def auth_plataforma_ti(escenario_plataforma_datos: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_plataforma_datos['token_ti']}"}


@pytest_asyncio.fixture
async def escenario_dashboards(db_session: AsyncSession, escenario_pos: dict) -> dict:
    """Feature 009: datos fuente reales para que los jobs de publicación produzcan
    un snapshot con valores (no ClickHouse — modo fixture, quickstart.md).

    - `Gerente_General` + `Jefe_Comercial` + `Jefe_Finanzas` + `Jefe_TI` con token.
    - una venta confirmada (OE-1/OE-2), dos encuestas de clima laboral (OE-8, AVG=8.0),
      una merma validada (OE-3).
    - dashboards operativos de la tienda: `alertas_reposicion` y `cuadre_caja` frescos
      (hoy), `seguimiento_merma` con más de un día de antigüedad (US3, FR-007).
    """
    from datetime import UTC, datetime, timedelta

    s = db_session
    e = escenario_pos
    tienda_id = e["tienda_id"]
    ahora = datetime.now(UTC).replace(tzinfo=None)

    async def _rol(nombre: str) -> int:
        return await s.scalar(text("SELECT role_id FROM roles WHERE nombre = :n"), {"n": nombre})

    _roles = ("Gerente_General", "Jefe_Comercial", "Jefe_Finanzas", "Jefe_TI", "Jefe_Marketing")
    tokens = {
        rol: await _token(s, role_id=await _rol(rol), tienda_id=tienda_id) for rol in _roles
    }

    # --- OE-1/OE-2: una venta confirmada
    venta_id = await s.scalar(
        text(
            "INSERT INTO ventas (tienda_id, cajero_id, fecha_hora, semana, total, estado) "
            "VALUES (:t, :c, :f, 1, 20, 'confirmada') RETURNING venta_id"
        ),
        {"t": tienda_id, "c": e["cajero_id"], "f": ahora},
    )
    await s.execute(
        text(
            "INSERT INTO venta_detalle (venta_id, product_id, cantidad, sales_value) "
            "VALUES (:v, :p, 8, 20.00)"
        ),
        {"v": venta_id, "p": e["product_id"]},
    )

    # --- OE-8: clima laboral (AVG de 7.5 y 8.5 = 8.0)
    for res in ("7.50", "8.50"):
        await s.execute(
            text(
                "INSERT INTO clima_laboral (tienda_id, periodo, resultado_promedio) "
                "VALUES (:t, '2026-S1', :r)"
            ),
            {"t": tienda_id, "r": res},
        )

    # --- OE-3: una merma validada + (misma fila) fuente 'seguimiento_merma' ANTIGUA
    await s.execute(
        text(
            "INSERT INTO mermas "
            "(product_id, tienda_id, cantidad, causa, valor, empleado_id, fecha) "
            "VALUES (:p, :t, 3, 'caducidad', 12.00, :emp, :f)"
        ),
        {"p": e["product_id"], "t": tienda_id, "emp": e["encargado_id"],
         "f": (ahora - timedelta(days=3)).date()},
    )

    # --- operativo fresco: alertas_reposicion (hoy)
    await s.execute(
        text(
            "INSERT INTO alertas_inventario (tipo, product_id, tienda_id, estado, fecha_generada) "
            "VALUES ('reposicion', :p, :t, 'pendiente', :f)"
        ),
        {"p": e["product_id"], "t": tienda_id, "f": ahora},
    )
    # --- operativo fresco: cuadre_caja (hoy)
    caja_id = await s.scalar(
        text("INSERT INTO cajas (tienda_id, nombre) VALUES (:t, 'Caja DASH') RETURNING caja_id"),
        {"t": tienda_id},
    )
    await s.execute(
        text(
            "INSERT INTO cierre_caja "
            "(caja_id, cajero_id, total_esperado, total_registrado, fecha_hora) "
            "VALUES (:c, :caj, 100.00, 100.00, :f)"
        ),
        {"c": caja_id, "caj": e["cajero_id"], "f": ahora},
    )
    await s.flush()

    return {
        **e,
        "tokens": tokens,
        "venta_id": venta_id,
        "caja_id": caja_id,
    }


@pytest.fixture
def auth_gerente_general(escenario_dashboards: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_dashboards['tokens']['Gerente_General']}"}


@pytest.fixture
def auth_dash_comercial(escenario_dashboards: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_dashboards['tokens']['Jefe_Comercial']}"}


@pytest.fixture
def auth_dash_ti(escenario_dashboards: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_dashboards['tokens']['Jefe_TI']}"}
