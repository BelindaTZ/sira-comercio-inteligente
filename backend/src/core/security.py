"""Autenticación JWT + RBAC de dos niveles (T008).

La *emisión* del token (login) la entrega la feature 008; aquí solo se **consume**:
se decodifica, se extrae el rol y se valida contra `role_permisos_modulo` /
`role_permisos_tabla` ya existentes en el esquema (Principio IV). Mientras 008 no
exista, un token de prueba firmado con `JWT_SECRET` y estos claims es suficiente.
"""

from __future__ import annotations

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


class Principal(BaseModel):
    """Identidad autenticada extraída del JWT."""

    usuario_id: int | None = None
    empleado_id: int
    role_id: int
    rol: str | None = None
    tienda_id: int | None = None


def decode_token(token: str) -> Principal:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expirado") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido") from exc

    try:
        return Principal(
            usuario_id=payload.get("usuario_id"),
            empleado_id=payload["empleado_id"],
            role_id=payload["role_id"],
            rol=payload.get("rol"),
            tienda_id=payload.get("tienda_id"),
        )
    except KeyError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"Claim obligatorio ausente en el token: {exc}",
        ) from exc


async def get_current_principal(
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Falta el header Authorization: Bearer <token>",
        )
    return decode_token(authorization.split(" ", 1)[1].strip())


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


async def _has_permission(
    db: AsyncSession, role_id: int, modulo: str, tabla: str, action: Action
) -> bool:
    can_col = _CAN_COLUMN[action]
    # La FK compuesta de role_permisos_tabla ya obliga a tener la fila de módulo;
    # el JOIN a modulos aquí solo traduce el nombre a id.
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
    """Devuelve una dependencia de FastAPI que exige `action` sobre `modulo`→`tabla`."""

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
