"""Esquemas Pydantic del módulo Sistema — `contracts/auth-administracion-sistema.md`."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- autenticación
class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)


class LoginOut(BaseModel):
    access_token: str
    usuario_id: int
    expira_en: int  # segundos


class CambiarPasswordIn(BaseModel):
    password_actual: str = Field(min_length=1)
    password_nueva: str = Field(min_length=8, max_length=128)


class PerfilModuloOut(BaseModel):
    nombre: str
    puede_ver: bool
    puede_editar: bool


class PerfilTablaOut(BaseModel):
    """Una tabla que el rol puede leer, con su módulo. El frontend la usa para
    ocultar ítems de navegación cuyo permiso de tabla es más estrecho que el del
    módulo (p. ej. `Encargado_Tienda` ve el módulo `Comercial` sólo por
    `revision_margen_bajo`, no por `productos`)."""

    modulo: str
    nombre_tabla: str
    can_select: bool
    can_editar: bool


class PerfilOut(BaseModel):
    """`GET /auth/me` — identidad de la sesión + módulos visibles para el rol.

    El JWT sólo transporta `usuario_id`; el frontend necesita esto para pintar la
    navegación según el rol (Principio XII) sin exponer la tabla RBAC completa.
    """

    usuario_id: int
    empleado_id: int
    role_id: int
    rol: str | None
    tienda_id: int | None
    nombre: str | None
    username: str | None
    modulos: list[PerfilModuloOut]
    tablas: list[PerfilTablaOut] = []


class RecuperarPasswordIn(BaseModel):
    email: str = Field(min_length=3, max_length=150)


class ConfirmarRecuperacionIn(BaseModel):
    token: str = Field(min_length=1, max_length=128)
    password_nueva: str = Field(min_length=8, max_length=128)


# ---------------------------------------------------------------- cuentas
class CrearUsuarioIn(BaseModel):
    empleado_id: int
    username: str = Field(min_length=1, max_length=50)
    password_inicial: str = Field(min_length=8, max_length=128)
    role_id: int


class AsignarRolIn(BaseModel):
    role_id: int


class UsuarioOut(BaseModel):
    usuario_id: int
    empleado_id: int
    role_id: int
    username: str
    activo: bool
    ultimo_login: datetime | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------- RBAC admin
class PermisoModuloOut(BaseModel):
    modulo_id: int
    nombre: str
    puede_ver: bool
    puede_editar: bool


class PermisoModuloIn(BaseModel):
    puede_ver: bool
    puede_editar: bool


class PermisoTablaOut(BaseModel):
    nombre_tabla: str
    can_select: bool
    can_insert: bool
    can_update: bool
    can_delete: bool


class PermisoTablaIn(BaseModel):
    can_select: bool = False
    can_insert: bool = False
    can_update: bool = False
    can_delete: bool = False


# ---------------------------------------------------------------- auditoría
class ReporteAuditoriaItem(BaseModel):
    usuario_id: int | None
    username: str | None
    logins_exitosos: int
    intentos_fallidos: int
    acciones_registradas: int
    ultimo_login: datetime | None
