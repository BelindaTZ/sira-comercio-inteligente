from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class CuponEnviado(Base):
    """`cupon_enviado` (ronda 2, feature 002) — registro del envío de un cupón de
    hito. `entregado` se marca según el resultado de SendGrid, pero el registro
    existe aunque el correo falle (Principio II) (FR-013/FR-014)."""

    __tablename__ = "cupon_enviado"

    envio_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    evento_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("eventos_cliente.evento_id", ondelete="CASCADE")
    )
    household_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.household_id", ondelete="CASCADE"), nullable=False
    )
    coupon_upc: Mapped[str] = mapped_column(String(20), nullable=False)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campanas.campaign_id"), nullable=False
    )
    fecha_envio: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    entregado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # feature 005: regla de afinidad que originó el cupón (NULL para cupones de hito
    # o de campañas de reactivación de 002).
    regla_afinidad_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("regla_afinidad.regla_id")
    )
