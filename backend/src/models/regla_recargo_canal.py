from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ReglaRecargoCanal(Base):
    """`regla_recargo_canal` (001, US4, migración 0024) — recargo transversal por
    canal de venta sobre el PVP físico. El PVP por canal se calcula
    `precio_base * (1 + markup_pct/100)`; no se guarda un precio por producto.
    """

    __tablename__ = "regla_recargo_canal"

    canal: Mapped[str] = mapped_column(String(30), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    markup_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    descripcion: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
