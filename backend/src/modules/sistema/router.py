"""Routers del módulo Sistema — `contracts/auth-administracion-sistema.md`.

`auth_router` (prefijo `/auth`): login, recuperación de contraseña y cambio de
contraseña propia. `POST /auth/login`, `POST /auth/recuperar-password` y
`POST /auth/recuperar-password/confirmar` son los únicos endpoints sin
autenticación de todo el sistema (por definición).

`sistema_router` (prefijo `/sistema`): cuentas de usuario, administración de RBAC
y reporte de auditoría — RBAC módulo `Sistema` para `Jefe_TI`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.security import (
    CurrentPrincipal,
    Principal,
    crear_access_token,
    require_permission,
)
from src.modules.sistema.repository import SistemaRepository
from src.modules.sistema.schemas import (
    AsignarRolIn,
    CambiarPasswordIn,
    ConfirmarRecuperacionIn,
    CrearUsuarioIn,
    LoginIn,
    LoginOut,
    PermisoModuloIn,
    PermisoModuloOut,
    PermisoTablaIn,
    PermisoTablaOut,
    RecuperarPasswordIn,
    ReporteAuditoriaItem,
    UsuarioOut,
)
from src.modules.sistema.service import SistemaService

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_GENERIC_401 = "Credenciales inválidas o cuenta inactiva"


def _svc(session: SessionDep) -> SistemaService:
    return SistemaService(SistemaRepository(session))


ServiceDep = Annotated[SistemaService, Depends(_svc)]

_admin_usuarios_ver = require_permission("Sistema", "usuarios", "select")
_admin_usuarios = require_permission("Sistema", "usuarios", "update")
_admin_usuarios_crear = require_permission("Sistema", "usuarios", "insert")
_admin_permisos_modulo_ver = require_permission("Sistema", "role_permisos_modulo", "select")
_admin_permisos_modulo = require_permission("Sistema", "role_permisos_modulo", "update")
_admin_permisos_tabla_ver = require_permission("Sistema", "role_permisos_tabla", "select")
_admin_permisos_tabla = require_permission("Sistema", "role_permisos_tabla", "update")
_ve_auditoria = require_permission("Sistema", "auditoria_log", "select")


# ============================================================ auth (público)
auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/login", response_model=LoginOut)
async def login(data: LoginIn, session: SessionDep, svc: ServiceDep) -> LoginOut:
    resultado = await svc.login(data.username, data.password)
    # El intento (exitoso o no) debe persistir aunque respondamos 401.
    await session.commit()
    if not resultado["ok"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _GENERIC_401)
    usuario = resultado["usuario"]
    token, ttl = crear_access_token(usuario.usuario_id)
    return LoginOut(access_token=token, usuario_id=usuario.usuario_id, expira_en=ttl)


@auth_router.post("/recuperar-password", status_code=status.HTTP_200_OK)
async def recuperar_password(data: RecuperarPasswordIn, svc: ServiceDep) -> dict:
    await svc.solicitar_recuperacion(data.email)
    return {"mensaje": "Si el correo corresponde a una cuenta, se envió un enlace de recuperación"}


@auth_router.post("/recuperar-password/confirmar", status_code=status.HTTP_200_OK)
async def confirmar_recuperacion(data: ConfirmarRecuperacionIn, svc: ServiceDep) -> dict:
    await svc.confirmar_recuperacion(data.token, data.password_nueva)
    return {"mensaje": "Contraseña actualizada"}


@auth_router.patch("/mi-password", status_code=status.HTTP_200_OK)
async def cambiar_mi_password(
    data: CambiarPasswordIn, svc: ServiceDep, principal: CurrentPrincipal
) -> dict:
    await svc.cambiar_password_propia(
        principal.usuario_id, data.password_actual, data.password_nueva
    )
    return {"mensaje": "Contraseña actualizada"}


# ============================================================ sistema (Jefe_TI)
sistema_router = APIRouter(prefix="/sistema", tags=["sistema"])


@sistema_router.post(
    "/usuarios", status_code=status.HTTP_201_CREATED, response_model=UsuarioOut
)
async def crear_usuario(
    data: CrearUsuarioIn, svc: ServiceDep, _: Annotated[Principal, Depends(_admin_usuarios_crear)]
) -> UsuarioOut:
    return UsuarioOut.model_validate(
        await svc.crear_cuenta(
            empleado_id=data.empleado_id,
            username=data.username,
            password_inicial=data.password_inicial,
            role_id=data.role_id,
        )
    )


@sistema_router.get("/usuarios/{usuario_id}", response_model=UsuarioOut)
async def obtener_usuario(
    usuario_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_admin_usuarios_ver)]
) -> UsuarioOut:
    return UsuarioOut.model_validate(await svc.get_usuario(usuario_id))


@sistema_router.patch("/usuarios/{usuario_id}/rol", response_model=UsuarioOut)
async def asignar_rol(
    usuario_id: int,
    data: AsignarRolIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_admin_usuarios)],
) -> UsuarioOut:
    return UsuarioOut.model_validate(await svc.asignar_rol(usuario_id, data.role_id))


@sistema_router.get(
    "/roles/{role_id}/permisos-modulo", response_model=list[PermisoModuloOut]
)
async def listar_permisos_modulo(
    role_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_admin_permisos_modulo_ver)]
) -> list[PermisoModuloOut]:
    return [PermisoModuloOut(**p) for p in await svc.listar_permisos_modulo(role_id)]


@sistema_router.put(
    "/roles/{role_id}/permisos-modulo/{modulo_id}", response_model=PermisoModuloOut
)
async def definir_permiso_modulo(
    role_id: int,
    modulo_id: int,
    data: PermisoModuloIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_admin_permisos_modulo)],
) -> PermisoModuloOut:
    return PermisoModuloOut(
        **await svc.definir_permiso_modulo(
            role_id, modulo_id, puede_ver=data.puede_ver, puede_editar=data.puede_editar
        )
    )


@sistema_router.get(
    "/roles/{role_id}/permisos-tabla", response_model=list[PermisoTablaOut]
)
async def listar_permisos_tabla(
    role_id: int,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_admin_permisos_tabla_ver)],
    modulo_id: int | None = None,
) -> list[PermisoTablaOut]:
    return [PermisoTablaOut(**p) for p in await svc.listar_permisos_tabla(role_id, modulo_id)]


@sistema_router.put(
    "/roles/{role_id}/permisos-tabla/{modulo_id}/{nombre_tabla}",
    response_model=PermisoTablaOut,
)
async def definir_permiso_tabla(
    role_id: int,
    modulo_id: int,
    nombre_tabla: str,
    data: PermisoTablaIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_admin_permisos_tabla)],
) -> PermisoTablaOut:
    return PermisoTablaOut(
        **await svc.definir_permiso_tabla(
            role_id,
            modulo_id,
            nombre_tabla,
            can_select=data.can_select,
            can_insert=data.can_insert,
            can_update=data.can_update,
            can_delete=data.can_delete,
        )
    )


@sistema_router.get("/auditoria/reporte-mensual", response_model=list[ReporteAuditoriaItem])
async def reporte_auditoria(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ve_auditoria)],
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2000),
) -> list[ReporteAuditoriaItem]:
    return [ReporteAuditoriaItem(**r) for r in await svc.reporte_auditoria(mes, anio)]
