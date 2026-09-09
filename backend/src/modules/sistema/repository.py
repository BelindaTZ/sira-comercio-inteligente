"""SistemaRepository (feature 008) — acceso a datos de cuentas de usuario,
enlaces de recuperación, intentos de login, RBAC y auditoría. Sin lógica de
negocio (Principio XI)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.intento_login import IntentoLogin
from src.models.recuperacion_password import RecuperacionPassword
from src.models.role_permiso import RolePermisoModulo, RolePermisoTabla
from src.models.usuario import Usuario


class SistemaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def flush(self) -> None:
        await self.session.flush()

    # ---------------------------------------------------------- usuarios
    async def usuario_por_username(self, username: str) -> Usuario | None:
        stmt = select(Usuario).where(func.lower(Usuario.username) == username.lower())
        return (await self.session.scalars(stmt)).first()

    async def usuario_por_id(self, usuario_id: int) -> Usuario | None:
        return await self.session.get(Usuario, usuario_id)

    async def usuario_por_empleado(self, empleado_id: int) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.empleado_id == empleado_id)
        return (await self.session.scalars(stmt)).first()

    async def crear_usuario(self, usuario: Usuario) -> Usuario:
        self.session.add(usuario)
        await self.session.flush()
        await self.session.refresh(usuario)
        return usuario

    async def actualizar_ultimo_login(self, usuario: Usuario, momento: datetime) -> None:
        usuario.ultimo_login = momento
        await self.session.flush()

    async def registrar_intento_login(
        self, *, usuario_id: int | None, username: str, exitoso: bool
    ) -> None:
        self.session.add(
            IntentoLogin(usuario_id=usuario_id, username_intentado=username[:50], exitoso=exitoso)
        )
        await self.session.flush()

    async def empleado_email(self, email: str) -> int | None:
        return await self.session.scalar(
            text("SELECT empleado_id FROM empleados WHERE lower(email) = lower(:e)"), {"e": email}
        )

    async def empleado_de_usuario(self, usuario_id: int) -> dict | None:
        row = (
            await self.session.execute(
                text(
                    "SELECT e.empleado_id, e.email, e.nombre FROM empleados e "
                    "JOIN usuarios u ON u.empleado_id = e.empleado_id WHERE u.usuario_id = :uid"
                ),
                {"uid": usuario_id},
            )
        ).first()
        return dict(row._mapping) if row else None

    # ---------------------------------------------------------- recuperación
    async def crear_token_recuperacion(
        self, *, usuario_id: int, token: str, expira: datetime
    ) -> RecuperacionPassword:
        fila = RecuperacionPassword(usuario_id=usuario_id, token=token, fecha_expiracion=expira)
        self.session.add(fila)
        await self.session.flush()
        return fila

    async def token_recuperacion(self, token: str) -> RecuperacionPassword | None:
        stmt = select(RecuperacionPassword).where(RecuperacionPassword.token == token)
        return (await self.session.scalars(stmt)).first()

    async def marcar_token_usado(self, fila: RecuperacionPassword) -> None:
        fila.usado = True
        await self.session.flush()

    async def set_password_hash(self, usuario: Usuario, password_hash: str) -> None:
        usuario.password_hash = password_hash
        await self.session.flush()

    # ---------------------------------------------------------- RBAC
    async def role_existe(self, role_id: int) -> bool:
        return (
            await self.session.scalar(
                text("SELECT 1 FROM roles WHERE role_id = :r"), {"r": role_id}
            )
        ) is not None

    async def permisos_modulo_de_rol(self, role_id: int) -> list[dict]:
        rows = await self.session.execute(
            text("""
                SELECT m.modulo_id, m.nombre,
                       COALESCE(rpm.puede_ver, false) AS puede_ver,
                       COALESCE(rpm.puede_editar, false) AS puede_editar
                FROM modulos m
                LEFT JOIN role_permisos_modulo rpm
                  ON rpm.modulo_id = m.modulo_id AND rpm.role_id = :r
                ORDER BY m.nombre
            """),
            {"r": role_id},
        )
        return [dict(r._mapping) for r in rows]

    async def tablas_legibles_de_rol(self, role_id: int) -> list[dict]:
        """Tablas que el rol puede leer (con su módulo), para que el frontend
        oculte ítems de navegación cuyo permiso de tabla es más estrecho que el
        del módulo. Sólo `can_select = true`."""
        rows = await self.session.execute(
            text("""
                SELECT m.nombre AS modulo, rpt.nombre_tabla,
                       rpt.can_select,
                       (rpt.can_insert OR rpt.can_update OR rpt.can_delete) AS can_editar
                FROM role_permisos_tabla rpt
                JOIN modulos m ON m.modulo_id = rpt.modulo_id
                WHERE rpt.role_id = :r AND rpt.can_select
                ORDER BY m.nombre, rpt.nombre_tabla
            """),
            {"r": role_id},
        )
        return [dict(r._mapping) for r in rows]

    async def tienda_de(self, tienda_id: int) -> dict | None:
        """Datos de la sucursal de la sesión — el shell muestra su nombre/ciudad
        en la sub-barra de contexto (Principio XII: el operador debe saber en qué
        tienda está)."""
        row = (
            await self.session.execute(
                text(
                    "SELECT tienda_id, codigo, nombre, ciudad FROM tiendas "
                    "WHERE tienda_id = :t"
                ),
                {"t": tienda_id},
            )
        ).first()
        return dict(row._mapping) if row is not None else None

    async def pin_de_empleado(self, empleado_id: int) -> str | None:
        return await self.session.scalar(
            text("SELECT pin_autorizacion FROM empleados WHERE empleado_id = :e"),
            {"e": empleado_id},
        )

    async def modulo_id_existe(self, modulo_id: int) -> bool:
        return (
            await self.session.scalar(
                text("SELECT 1 FROM modulos WHERE modulo_id = :m"), {"m": modulo_id}
            )
        ) is not None

    async def upsert_permiso_modulo(
        self, *, role_id: int, modulo_id: int, puede_ver: bool, puede_editar: bool
    ) -> None:
        stmt = pg_insert(RolePermisoModulo).values(
            role_id=role_id, modulo_id=modulo_id, puede_ver=puede_ver, puede_editar=puede_editar
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["role_id", "modulo_id"],
            set_={"puede_ver": puede_ver, "puede_editar": puede_editar},
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def tiene_permiso_modulo(self, role_id: int, modulo_id: int) -> bool:
        return (
            await self.session.scalar(
                text(
                    "SELECT 1 FROM role_permisos_modulo WHERE role_id = :r AND modulo_id = :m"
                ),
                {"r": role_id, "m": modulo_id},
            )
        ) is not None

    async def permisos_tabla_de_rol(self, role_id: int, modulo_id: int | None) -> list[dict]:
        cond = "rpt.role_id = :r"
        params: dict = {"r": role_id}
        if modulo_id is not None:
            cond += " AND rpt.modulo_id = :m"
            params["m"] = modulo_id
        rows = await self.session.execute(
            text(
                "SELECT rpt.nombre_tabla, rpt.can_select, rpt.can_insert, rpt.can_update, "
                f"rpt.can_delete FROM role_permisos_tabla rpt WHERE {cond} "
                "ORDER BY rpt.modulo_id, rpt.nombre_tabla"
            ),
            params,
        )
        return [dict(r._mapping) for r in rows]

    async def upsert_permiso_tabla(
        self,
        *,
        role_id: int,
        modulo_id: int,
        nombre_tabla: str,
        can_select: bool,
        can_insert: bool,
        can_update: bool,
        can_delete: bool,
    ) -> None:
        stmt = pg_insert(RolePermisoTabla).values(
            role_id=role_id,
            modulo_id=modulo_id,
            nombre_tabla=nombre_tabla,
            can_select=can_select,
            can_insert=can_insert,
            can_update=can_update,
            can_delete=can_delete,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["role_id", "modulo_id", "nombre_tabla"],
            set_={
                "can_select": can_select,
                "can_insert": can_insert,
                "can_update": can_update,
                "can_delete": can_delete,
            },
        )
        await self.session.execute(stmt)
        await self.session.flush()

    # ---------------------------------------------------------- auditoría
    async def reporte_auditoria_mensual(self, mes: int, anio: int) -> list[dict]:
        rows = await self.session.execute(
            text("""
                WITH li AS (
                    SELECT usuario_id,
                           COUNT(*) FILTER (WHERE exitoso) AS logins_exitosos,
                           COUNT(*) FILTER (WHERE NOT exitoso) AS intentos_fallidos
                    FROM intentos_login
                    WHERE EXTRACT(MONTH FROM fecha_hora) = :mes
                      AND EXTRACT(YEAR FROM fecha_hora) = :anio
                    GROUP BY usuario_id
                ),
                al AS (
                    SELECT usuario_id, COUNT(*) AS acciones_registradas
                    FROM auditoria_log
                    WHERE EXTRACT(MONTH FROM fecha_hora) = :mes
                      AND EXTRACT(YEAR FROM fecha_hora) = :anio
                    GROUP BY usuario_id
                )
                SELECT u.usuario_id, u.username, u.ultimo_login,
                       COALESCE(li.logins_exitosos, 0) AS logins_exitosos,
                       COALESCE(li.intentos_fallidos, 0) AS intentos_fallidos,
                       COALESCE(al.acciones_registradas, 0) AS acciones_registradas
                FROM usuarios u
                LEFT JOIN li ON li.usuario_id = u.usuario_id
                LEFT JOIN al ON al.usuario_id = u.usuario_id
                WHERE li.usuario_id IS NOT NULL OR al.usuario_id IS NOT NULL
                UNION ALL
                SELECT NULL, NULL, NULL,
                       COALESCE(SUM(logins_exitosos), 0), COALESCE(SUM(intentos_fallidos), 0), 0
                FROM li WHERE usuario_id IS NULL
                HAVING COALESCE(SUM(intentos_fallidos), 0) > 0
            """),
            {"mes": mes, "anio": anio},
        )
        return [dict(r._mapping) for r in rows]
