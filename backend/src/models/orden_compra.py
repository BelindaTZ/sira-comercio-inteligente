from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

ORDEN_ESTADOS = ("pendiente", "aprobada", "confirmada", "recibida", "rechazada", "cancelada")
ORDEN_TIPOS = ("programada", "especial")
CANALES_RESPUESTA = ("correo", "whatsapp", "telefono", "presencial", "otro")


class OrdenCompra(Base):
    """`ordenes_compra` — `tipo` y `motivo_desviacion` (FR-024/FR-029) de 001."""

    __tablename__ = "ordenes_compra"

    orden_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    proveedor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("proveedores.proveedor_id"), nullable=False
    )
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    empleado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="programada")
    motivo_desviacion: Mapped[str | None] = mapped_column(Text)
    # feature 018 — respuesta del proveedor registrada por un actor humano
    proveedor_confirmo: Mapped[bool | None] = mapped_column(Boolean)
    respuesta_proveedor: Mapped[str | None] = mapped_column(Text)
    canal_respuesta: Mapped[str | None] = mapped_column(String(20))
    fecha_respuesta: Mapped[datetime | None] = mapped_column(DateTime)
    empleado_respuesta_id: Mapped[int | None] = mapped_column(Integer)
