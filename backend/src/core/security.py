"""Autenticación JWT + RBAC de dos niveles.

Feature 008 convierte esto de "token de prueba" a mecanismo real:

- El JWT emitido al iniciar sesión transporta **sólo** `usuario_id` (+ expiración)
  — nunca el rol ni los permisos (research.md Decisión 1). En cada request el
  backend resuelve el rol vigente y los permisos consultando PostgreSQL, de modo
  que un cambio de rol/permiso o una baja de cuenta tienen efecto inmediato sin
  nuevo login ni lista de revocación.
- `role_permisos_modulo` / `role_permisos_tabla` gobiernan el acceso a datos
  (Principio IV). Los únicos endpoints sin RBAC son `POST /api/auth/login` y
  `POST /api/auth/recuperar-password` (públicos por definición).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

import jwt
from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_session

Action = Literal["select", "insert", "update", "delete"]

_CAN_COLUMN: dict[Action, str] = {
    "select": "can_select",
    "insert": "can_insert",
    "update": "can_update",
    "delete": "can_delete",
}

# 401 idéntico para credenciales incorrectas y cuenta inactiva (FR-002/FR-003).
_GENERIC_401 = "Credenciales inválidas o cuenta inactiva"


class Principal(BaseModel):
    """Identidad autenticada, resuelta contra la BD en cada request."""

    usuario_id: int
    empleado_id: int
    role_id: int
    rol: str | None = None
    tienda_id: int | None = None


# --------------------------------------------------------------------- emisión
def crear_access_token(usuario_id: int) -> tuple[str, int]:
    """Devuelve `(jwt, segundos_de_vigencia)`. El único claim de negocio es
    `usuario_id` (research.md Decisión 1)."""
    ttl = settings.jwt_expiration_minutes * 60
    payload = {
        "usuario_id": usuario_id,
        "exp": datetime.now(UTC) + timedelta(seconds=ttl),
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, ttl


# ------------------------------------------------------------------- consumo
def decode_usuario_id(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión expirada") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido") from exc
    try:
        return int(payload["usuario_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido") from exc


async def _resolver_principal(db: AsyncSession, usuario_id: int) -> Principal:
    row = (
        await db.execute(
            text("""
                SELECT u.usuario_id, u.empleado_id, u.role_id, u.activo,
                       r.nombre AS rol, e.tienda_id
                FROM usuarios u
                JOIN roles r ON r.role_id = u.role_id
                JOIN empleados e ON e.empleado_id = u.empleado_id
                WHERE u.usuario_id = :uid
            """),
            {"uid": usuario_id},
        )
    ).first()
    if row is None or not row.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _GENERIC_401)
    return Principal(
        usuario_id=row.usuario_id,
        empleado_id=row.empleado_id,
        role_id=row.role_id,
        rol=row.rol,
        tienda_id=row.tienda_id,
    )


async def get_current_principal(
    db: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Falta el header Authorization: Bearer <token>"
        )
    usuario_id = decode_usuario_id(authorization.split(" ", 1)[1].strip())
    return await _resolver_principal(db, usuario_id)


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


async def _has_permission(
    db: AsyncSession, role_id: int, modulo: str, tabla: str, action: Action
) -> bool:
    can_col = _CAN_COLUMN[action]
    modulo_ok = "puede_ver" if action == "select" else "puede_editar"
    row = await db.execute(
        text(f"""
            SELECT rpt.{can_col} AS permitido
            FROM role_permisos_tabla rpt
            JOIN modulos m ON m.modulo_id = rpt.modulo_id
            JOIN role_permisos_modulo rpm
              ON rpm.role_id = rpt.role_id AND rpm.modulo_id = rpt.modulo_id
            WHERE rpt.role_id = :role_id
              AND m.nombre = :modulo
              AND rpt.nombre_tabla = :tabla
              AND rpm.{modulo_ok} = true
            """),
        {"role_id": role_id, "modulo": modulo, "tabla": tabla},
    )
    result = row.first()
    return bool(result and result.permitido)


def require_permission(modulo: str, tabla: str, action: Action):
    """Dependencia de FastAPI que exige `action` sobre `modulo`→`tabla`."""

    async def _dependency(
        principal: CurrentPrincipal,
        db: Annotated[AsyncSession, Depends(get_session)],
    ) -> Principal:
        if not await _has_permission(db, principal.role_id, modulo, tabla, action):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"El rol no tiene permiso {action} sobre {modulo}.{tabla}",
            )
        return principal

    return _dependency
