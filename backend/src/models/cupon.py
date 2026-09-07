from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Cupon(Base):
    """`cupones` — catálogo cupón↔producto↔campaña (PK compuesta, del dataset)."""

    __tablename__ = "cupones"

    coupon_upc: Mapped[str] = mapped_column(String(20), primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("productos.product_id"), primary_key=True, autoincrement=False
    )
    campaign_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("campanas.campaign_id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
    )
