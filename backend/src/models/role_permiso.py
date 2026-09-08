from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class RolePermisoModulo(Base):
    """`role_permisos_modulo` (desde 001) — nivel 1 del RBAC. Feature 008 la
    administra vía CRUD; 001-007 sólo la consultaban para enforcement."""

    __tablename__ = "role_permisos_modulo"

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    modulo_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    puede_ver: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    puede_editar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class RolePermisoTabla(Base):
    """`role_permisos_tabla` (desde 001) — nivel 2 del RBAC. La FK compuesta a
    `role_permisos_modulo` garantiza por esquema que un permiso de tabla no puede
    existir sin el permiso de módulo (FR-013, Edge Case)."""

    __tablename__ = "role_permisos_tabla"

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    modulo_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_tabla: Mapped[str] = mapped_column(String(60), primary_key=True)
    can_select: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_insert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_update: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_delete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
