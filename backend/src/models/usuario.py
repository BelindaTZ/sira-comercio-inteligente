from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Usuario(Base):
    """`usuarios` (desde 001, referenciada por FK; feature 008 la administra). 1:1
    con `empleados` (`empleado_id UNIQUE` — FR-008). `activo=false` bloquea el
    login (FR-003); lo inhabilita el trigger al dar de baja al empleado (Decisión
    4) y sólo el Jefe de TI lo reactiva (FR-015)."""

    __tablename__ = "usuarios"

    usuario_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empleado_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ultimo_login: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
