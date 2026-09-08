from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class IntentoLogin(Base):
    """`intentos_login` (feature 008, FR-016) — una fila por cada intento de
    inicio de sesión, exitoso o no. `usuario_id` es NULL cuando el
    `username_intentado` no corresponde a ninguna cuenta (research.md Decisión 3,
    distinta de `auditoria_log` que sólo modela cambios de fila)."""

    __tablename__ = "intentos_login"

    intento_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(Integer)
    username_intentado: Mapped[str] = mapped_column(String(50), nullable=False)
    exitoso: Mapped[bool] = mapped_column(Boolean, nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
