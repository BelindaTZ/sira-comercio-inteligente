"""Lógica pura de autenticación y RBAC (feature 008, Principio X).

Sin I/O — reglas testeables que el `SistemaService` y `security.py` orquestan:

  - `login_permitido` — el login sólo pasa si la cuenta existe, está activa y la
    contraseña coincide; el llamador responde el MISMO 401 en los tres fallos
    (FR-002/FR-003, no se distingue la causa)
  - `token_recuperacion_utilizable` — un enlace de recuperación sirve una sola vez
    y dentro de su vigencia (FR-010)
"""

from __future__ import annotations

from datetime import datetime


def login_permitido(*, usuario_existe: bool, usuario_activo: bool, password_ok: bool) -> bool:
    return bool(usuario_existe and usuario_activo and password_ok)


def token_recuperacion_utilizable(
    *, usado: bool, fecha_expiracion: datetime, ahora: datetime
) -> bool:
    return (not usado) and fecha_expiracion >= ahora
