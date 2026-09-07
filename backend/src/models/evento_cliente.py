from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

TIPO_EVENTO_CLIENTE = ("cumpleanos", "aniversario_registro")


class EventoCliente(Base):
    """`eventos_cliente` — hito de cliente (cumpleaños / aniversario de registro)
    generado por el job diario (FR-012). Cada evento puede disparar un cupón."""

    __tablename__ = "eventos_cliente"

    evento_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    household_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.household_id", ondelete="CASCADE"), nullable=False
    )
    tipo_evento: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
