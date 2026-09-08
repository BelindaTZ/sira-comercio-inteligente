"""Crea una cuenta de login por cada rol RBAC, para probar la app end-to-end.

NO forma parte del despliegue. Es un atajo de desarrollo: el sistema real crea
cuentas vía `POST /api/sistema/usuarios` (feature 008), pero eso exige un
`Jefe_TI` ya existente — este script rompe ese huevo-y-gallina.

Idempotente: si el `username` ya existe, no lo toca (salvo `--reset-password`).

Uso:
    cd backend
    .venv/Scripts/python -m scripts.seed_usuarios_demo
    .venv/Scripts/python -m scripts.seed_usuarios_demo --reset-password

Contraseña de TODAS las cuentas:  Sira2026!
Usuario = rol en minúsculas con punto (ver tabla al final de la salida).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import text
from src.core.database import AsyncSessionLocal
from src.shared.passwords import hash_password

if sys.platform == "win32":  # asyncpg + ProactorEventLoop no se llevan bien
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

PASSWORD = "Sira2026!"

# rol RBAC -> (username, ¿opera en una tienda concreta?)
# Prefijo `demo.` para no chocar con los usernames que fabrican los fixtures de
# pytest (`escenario_auth` usa `jefe.ti`, `jefe.rrhh`, `cajero.uno`) sobre la misma BD.
CUENTAS: list[tuple[str, str, bool]] = [
    ("Gerente_General", "demo.gerente", False),
    ("Jefe_TI", "demo.ti", False),
    ("Jefe_Comercial", "demo.comercial", False),
    ("Jefe_Marketing", "demo.marketing", False),
    ("Jefe_Operaciones", "demo.operaciones", False),
    ("Jefe_Finanzas", "demo.finanzas", False),
    ("Jefe_RRHH", "demo.rrhh", False),
    ("Encargado_Tienda", "demo.encargado", True),
    ("Reponedor", "demo.reponedor", True),
    ("Cajero", "demo.cajero", True),
]


async def _tienda_demo(session) -> int:
    # Prefiere una tienda real del dataset (con inventario/ventas) sobre la 'DEMO'.
    tid = await session.scalar(
        text(
            "SELECT tienda_id FROM tiendas WHERE codigo <> 'DEMO' "
            "ORDER BY tienda_id LIMIT 1"
        )
    )
    if tid is not None:
        return tid
    tid = await session.scalar(text("SELECT tienda_id FROM tiendas ORDER BY tienda_id LIMIT 1"))
    if tid is not None:
        return tid
    return await session.scalar(
        text(
            "INSERT INTO tiendas (codigo, nombre, ciudad, fecha_apertura) "
            "VALUES ('DEMO', 'SIRA Central (demo)', 'Quito', CURRENT_DATE) RETURNING tienda_id"
        )
    )


async def _puesto_demo(session) -> int:
    pid = await session.scalar(text("SELECT puesto_id FROM roles_puesto WHERE nombre = 'Demo'"))
    if pid is not None:
        return pid
    return await session.scalar(
        text(
            "INSERT INTO roles_puesto (nombre, descripcion) "
            "VALUES ('Demo', 'Puesto genérico para cuentas de prueba') RETURNING puesto_id"
        )
    )


async def seed(reset_password: bool) -> None:
    async with AsyncSessionLocal() as session:
        tienda_id = await _tienda_demo(session)
        puesto_id = await _puesto_demo(session)
        pwd_hash = hash_password(PASSWORD)

        creadas, existentes, actualizadas = [], [], []
        for rol, username, en_tienda in CUENTAS:
            role_id = await session.scalar(
                text("SELECT role_id FROM roles WHERE nombre = :n"), {"n": rol}
            )
            if role_id is None:
                print(f"  ! rol {rol} no existe en la BD — ¿aplicaste las migraciones?")
                continue

            ya = await session.scalar(
                text("SELECT usuario_id FROM usuarios WHERE username = :u"), {"u": username}
            )
            if ya is not None:
                if reset_password:
                    await session.execute(
                        text(
                            "UPDATE usuarios SET password_hash = :h, activo = true "
                            "WHERE usuario_id = :id"
                        ),
                        {"h": pwd_hash, "id": ya},
                    )
                    actualizadas.append(username)
                else:
                    existentes.append(username)
                continue

            empleado_id = await session.scalar(
                text(
                    "INSERT INTO empleados "
                    "(tienda_id, puesto_id, nombre, email, fecha_contratacion) "
                    "VALUES (:t, :p, :nombre, :email, CURRENT_DATE) RETURNING empleado_id"
                ),
                {
                    "t": tienda_id if en_tienda else None,
                    "p": puesto_id,
                    "nombre": f"Demo {rol}",
                    "email": f"{username}@sira.demo",
                },
            )
            await session.execute(
                text(
                    "INSERT INTO usuarios (empleado_id, role_id, username, password_hash) "
                    "VALUES (:e, :r, :u, :h)"
                ),
                {"e": empleado_id, "r": role_id, "u": username, "h": pwd_hash},
            )
            creadas.append(username)

        await session.commit()

    print()
    if creadas:
        print(f"  creadas:      {', '.join(creadas)}")
    if actualizadas:
        print(f"  password reseteada: {', '.join(actualizadas)}")
    if existentes:
        print(f"  ya existían (sin tocar): {', '.join(existentes)}")
    print()
    print(f"  Contraseña de todas: {PASSWORD}")
    print("  Login: http://localhost:5173/auth/login")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--reset-password",
        action="store_true",
        help="re-hashea la contraseña y reactiva las cuentas que ya existían",
    )
    asyncio.run(seed(ap.parse_args().reset_password))


if __name__ == "__main__":
    main()
