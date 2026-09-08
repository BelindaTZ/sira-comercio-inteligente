from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class RecuperacionPassword(Base):
    """`recuperacion_password` (feature 008, FR-009/FR-010) — enlace de un solo
    uso con vigencia limitada. Nunca se borra (Principio II, research.md Decisión
    2): al usarse se marca `usado=true`."""

    __tablename__ = "recuperacion_password"

    token_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(Integer, nullable=False)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    fecha_expiracion: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    usado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
