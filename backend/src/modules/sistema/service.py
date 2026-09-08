"""SistemaService — regla de negocio de autenticación, cuentas, RBAC, recuperación
de contraseña y auditoría (feature 008).

El login nunca distingue la causa del fallo (username inexistente vs. contraseña
incorrecta vs. cuenta inactiva) — FR-002/FR-003. Cada intento se registra en
`intentos_login`, exitoso o no.
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta

from src.integrations import sendgrid_client
from src.models.usuario import Usuario
from src.modules.sistema.repository import SistemaRepository
from src.shared.auth import login_permitido, token_recuperacion_utilizable
from src.shared.exceptions import ConflictError, DomainError, NotFoundError
from src.shared.passwords import hash_password, verify_password

logger = logging.getLogger("sira.sistema")

_RECUPERACION_VIGENCIA_MIN = 60


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class GoneError(DomainError):
    status_code = 410
    code = "gone"


class UnauthorizedError(DomainError):
    status_code = 401
    code = "unauthorized"


class SistemaService:
    def __init__(self, repo: SistemaRepository) -> None:
        self.repo = repo

    # ============================================================ US1: login
    async def login(self, username: str, password: str) -> dict:
        """FR-001 a FR-004. Devuelve `{ok, usuario}` — no lanza en el fallo para
        que el router pueda persistir el `intentos_login` antes de responder 401."""
        usuario = await self.repo.usuario_por_username(username)
        ok = login_permitido(
            usuario_existe=usuario is not None,
            usuario_activo=bool(usuario is not None and usuario.activo),
            password_ok=bool(
                usuario is not None and verify_password(password, usuario.password_hash)
            ),
        )
        await self.repo.registrar_intento_login(
            usuario_id=usuario.usuario_id if usuario is not None else None,
            username=username,
            exitoso=ok,
        )
        if ok:
            await self.repo.actualizar_ultimo_login(usuario, _ahora())
        return {"ok": ok, "usuario": usuario if ok else None}

    async def cambiar_password_propia(
        self, usuario_id: int, password_actual: str, password_nueva: str
    ) -> None:
        """FR-011 — self-service, sobre la propia cuenta (research.md Decisión 5)."""
        usuario = await self.repo.usuario_por_id(usuario_id)
        if usuario is None or not verify_password(password_actual, usuario.password_hash):
            raise UnauthorizedError("La contraseña actual no coincide")
        await self.repo.set_password_hash(usuario, hash_password(password_nueva))

    # ============================================================ US3: recuperación
    async def solicitar_recuperacion(self, email: str) -> None:
        """FR-009 — responde igual exista o no el email (anti-enumeración)."""
        empleado_id = await self.repo.empleado_email(email)
        if empleado_id is None:
            return
        usuario = await self.repo.usuario_por_empleado(empleado_id)
        if usuario is None or not usuario.activo:
            return
        token = secrets.token_urlsafe(48)
        await self.repo.crear_token_recuperacion(
            usuario_id=usuario.usuario_id,
            token=token,
            expira=_ahora() + timedelta(minutes=_RECUPERACION_VIGENCIA_MIN),
        )
        self._enviar_enlace(email, token)

    @staticmethod
    def _enviar_enlace(email: str, token: str) -> None:
        try:
            sendgrid_client.enviar_correo(
                to=email,
                subject="Recuperación de contraseña — SIRA",
                html=(
                    f"<p>Usa este enlace de un solo uso (válido {_RECUPERACION_VIGENCIA_MIN} "
                    f"minutos) para definir una nueva contraseña:</p>"
                    f"<p><code>{token}</code></p>"
                ),
            )
        except Exception:  # noqa: BLE001
            logger.info("SendGrid no disponible para el enlace de recuperación")

    async def confirmar_recuperacion(self, token: str, password_nueva: str) -> None:
        """FR-010 — token de un solo uso con vigencia limitada."""
        fila = await self.repo.token_recuperacion(token)
        if fila is None or not token_recuperacion_utilizable(
            usado=fila.usado, fecha_expiracion=fila.fecha_expiracion, ahora=_ahora()
        ):
            raise GoneError("El enlace de recuperación ya fue usado o venció")
        usuario = await self.repo.usuario_por_id(fila.usuario_id)
        if usuario is None:
            raise GoneError("El enlace de recuperación ya no es válido")
        await self.repo.set_password_hash(usuario, hash_password(password_nueva))
        await self.repo.marcar_token_usado(fila)

    # ============================================================ US2: cuentas
    async def crear_cuenta(
        self, *, empleado_id: int, username: str, password_inicial: str, role_id: int
    ) -> Usuario:
        """FR-007/FR-008 — una cuenta por empleado (la unicidad ya lo garantiza)."""
        if await self.repo.usuario_por_empleado(empleado_id) is not None:
            raise ConflictError(f"El empleado {empleado_id} ya tiene una cuenta")
        if not await self.repo.role_existe(role_id):
            raise NotFoundError(f"El rol {role_id} no existe")
        if await self.repo.usuario_por_username(username.strip()) is not None:
            raise ConflictError(f"El username '{username.strip()}' ya está en uso")
        return await self.repo.crear_usuario(
            Usuario(
                empleado_id=empleado_id,
                role_id=role_id,
                username=username.strip(),
                password_hash=hash_password(password_inicial),
                activo=True,
            )
        )

    async def get_usuario(self, usuario_id: int) -> Usuario:
        usuario = await self.repo.usuario_por_id(usuario_id)
        if usuario is None:
            raise NotFoundError(f"Usuario {usuario_id} no existe")
        return usuario

    # ============================================================ US4: RBAC admin
    async def asignar_rol(self, usuario_id: int, role_id: int) -> Usuario:
        """FR-012 — efecto inmediato: el JWT sólo lleva `usuario_id`, el rol se
        resuelve en cada request (research.md Decisión 1)."""
        usuario = await self.get_usuario(usuario_id)
        if not await self.repo.role_existe(role_id):
            raise NotFoundError(f"El rol {role_id} no existe")
        usuario.role_id = role_id
        await self.repo.flush()
        return usuario

    async def listar_permisos_modulo(self, role_id: int) -> list[dict]:
        await self._role_o_404(role_id)
        return await self.repo.permisos_modulo_de_rol(role_id)

    async def definir_permiso_modulo(
        self, role_id: int, modulo_id: int, *, puede_ver: bool, puede_editar: bool
    ) -> dict:
        await self._role_o_404(role_id)
        if not await self.repo.modulo_id_existe(modulo_id):
            raise NotFoundError(f"El módulo {modulo_id} no existe")
        await self.repo.upsert_permiso_modulo(
            role_id=role_id, modulo_id=modulo_id, puede_ver=puede_ver, puede_editar=puede_editar
        )
        return next(
            p
            for p in await self.repo.permisos_modulo_de_rol(role_id)
            if p["modulo_id"] == modulo_id
        )

    async def listar_permisos_tabla(self, role_id: int, modulo_id: int | None) -> list[dict]:
        await self._role_o_404(role_id)
        return await self.repo.permisos_tabla_de_rol(role_id, modulo_id)

    async def definir_permiso_tabla(
        self,
        role_id: int,
        modulo_id: int,
        nombre_tabla: str,
        *,
        can_select: bool,
        can_insert: bool,
        can_update: bool,
        can_delete: bool,
    ) -> dict:
        await self._role_o_404(role_id)
        if not await self.repo.tiene_permiso_modulo(role_id, modulo_id):
            raise ConflictError(
                "El rol no tiene acceso a ese módulo; otorga primero el permiso de módulo"
            )
        await self.repo.upsert_permiso_tabla(
            role_id=role_id,
            modulo_id=modulo_id,
            nombre_tabla=nombre_tabla,
            can_select=can_select,
            can_insert=can_insert,
            can_update=can_update,
            can_delete=can_delete,
        )
        return next(
            p
            for p in await self.repo.permisos_tabla_de_rol(role_id, modulo_id)
            if p["nombre_tabla"] == nombre_tabla
        )

    async def _role_o_404(self, role_id: int) -> None:
        if not await self.repo.role_existe(role_id):
            raise NotFoundError(f"El rol {role_id} no existe")

    # ============================================================ US5: auditoría
    async def reporte_auditoria(self, mes: int, anio: int) -> list[dict]:
        """FR-016 — accesos del mes agrupados por usuario."""
        return await self.repo.reporte_auditoria_mensual(mes, anio)
