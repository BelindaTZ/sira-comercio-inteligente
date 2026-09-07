from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class CuponRedimido(Base):
    """`cupon_redimido` — redención de cupón por un cliente (del dataset; alimenta
    el cálculo de tasa de retorno de una campaña)."""

    __tablename__ = "cupon_redimido"

    redemption_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    household_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.household_id", ondelete="CASCADE"), nullable=False
    )
    coupon_upc: Mapped[str] = mapped_column(String(20), nullable=False)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campanas.campaign_id"), nullable=False
    )
    redemption_date: Mapped[date] = mapped_column(Date, nullable=False)
