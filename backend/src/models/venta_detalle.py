from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class VentaDetalle(Base):
    """`venta_detalle` — incluye las columnas de descuento manual y margen que
    agregó la feature 003 (nullable, no las usa 001)."""

    __tablename__ = "venta_detalle"

    venta_detalle_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ventas.venta_id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    sales_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    retail_disc: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    coupon_disc: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    coupon_match_disc: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    # --- feature 003 (precios/márgenes): nullable, fuera de alcance de 001 ---
    motivo_descuento: Mapped[str | None] = mapped_column(String(200))
    empleado_aplica_id: Mapped[int | None] = mapped_column(Integer)
    empleado_autoriza_id: Mapped[int | None] = mapped_column(Integer)
    margen_real: Mapped[float | None] = mapped_column(Numeric(10, 2))
    margen_bajo_minimo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
