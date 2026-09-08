"""Hash y verificación de contraseñas (feature 008, Principio X).

bcrypt directo (sin `passlib`, que arrastra incompatibilidades de versión). Las
contraseñas nunca se guardan ni se registran en texto plano. bcrypt trunca a 72
bytes — se corta explícitamente para que una contraseña larga no rompa el hash.
"""

from __future__ import annotations

import bcrypt

_MAX_BYTES = 72


def _clip(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_clip(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_clip(password), password_hash.encode("ascii"))
    except ValueError:
        return False
