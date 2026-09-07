from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

MOVIMIENTO_TIPOS = (
    "entrada",
    "salida",
    "ajuste",
    "traslado_entrada",
    "traslado_salida",
)


class MovimientoInventario(Base):
    """`movimientos_inventario` — libro mayor de stock. El lote de origen del
    descuento FIFO se resuelve aquí (`referencia_tabla='venta_detalle'`), no como
    FK directa en `venta_detalle` (una línea puede tocar más de un lote)."""

    __tablename__ = "movimientos_inventario"
    __table_args__ = (
        ForeignKeyConstraint(
            ["product_id", "tienda_id"],
            ["inventario.product_id", "inventario.tienda_id"],
            name="fk_movimientos_inventario_producto_tienda",
        ),
    )

    movimiento_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    referencia_tabla: Mapped[str | None] = mapped_column(String(40))
    referencia_id: Mapped[int | None] = mapped_column(BigInteger)
    # Lote de origen/destino del movimiento (ronda 7, FR-005/FR-026).
    lote_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("lotes.lote_id"))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
