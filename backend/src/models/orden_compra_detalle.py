from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class OrdenCompraDetalle(Base):
    __tablename__ = "orden_compra_detalle"

    orden_detalle_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    orden_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ordenes_compra.orden_id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    costo_unitario: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
