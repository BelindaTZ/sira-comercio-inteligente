"""Fixtures compartidas de pytest (async).

Los tests de contrato/integración corren contra la BD PostgreSQL real vía Docker
(research.md #3), no con mocks. Cada test corre dentro de una transacción que se
revierte al final (aislamiento por savepoint), así no ensucian la base.

Requisitos: `docker compose up -d postgres` y `alembic upgrade head`.
`DATABASE_URL` apunta al Postgres de desarrollo (puerto 15432 por defecto).
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
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
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


def _token(*, empleado_id: int, role_id: int, rol: str, tienda_id: int | None = None) -> str:
    return jwt.encode(
        {
            "empleado_id": empleado_id,
            "role_id": role_id,
            "rol": rol,
            "tienda_id": tienda_id,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
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
        "token_cajero": _token(
            empleado_id=cajero_id, role_id=role_cajero, rol="Cajero", tienda_id=tienda_id
        ),
        "token_encargado": _token(
            empleado_id=encargado_id,
            role_id=role_encargado,
            rol="Encargado_Tienda",
            tienda_id=tienda_id,
        ),
    }


@pytest.fixture
def auth_cajero(escenario_pos: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_pos['token_cajero']}"}


@pytest.fixture
def auth_encargado(escenario_pos: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_pos['token_encargado']}"}


@pytest_asyncio.fixture
async def auth_jefe_comercial(db_session: AsyncSession, escenario_pos: dict) -> dict[str, str]:
    role_id = await db_session.scalar(
        text("SELECT role_id FROM roles WHERE nombre = 'Jefe_Comercial'")
    )
    token = _token(
        empleado_id=escenario_pos["encargado_id"],
        role_id=role_id,
        rol="Jefe_Comercial",
        tienda_id=escenario_pos["tienda_id"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_jefe_marketing(db_session: AsyncSession, escenario_pos: dict) -> dict[str, str]:
    role_id = await db_session.scalar(
        text("SELECT role_id FROM roles WHERE nombre = 'Jefe_Marketing'")
    )
    token = _token(
        empleado_id=escenario_pos["encargado_id"],
        role_id=role_id,
        rol="Jefe_Marketing",
        tienda_id=escenario_pos["tienda_id"],
    )
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
        "token_reponedor": _token(
            empleado_id=reponedor_id,
            role_id=role_reponedor,
            rol="Reponedor",
            tienda_id=tienda_id,
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
        "token_jefe_ops": _token(
            empleado_id=jefe_ops_id,
            role_id=role_jefe_ops,
            rol="Jefe_Operaciones",
            tienda_id=tienda_id,
        ),
        "token_jefe_fin": _token(
            empleado_id=jefe_fin_id,
            role_id=role_jefe_fin,
            rol="Jefe_Finanzas",
            tienda_id=tienda_id,
        ),
    }


@pytest.fixture
def auth_jefe_ops(escenario_compras: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_compras['token_jefe_ops']}"}


@pytest.fixture
def auth_jefe_fin(escenario_compras: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {escenario_compras['token_jefe_fin']}"}
