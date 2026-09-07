from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, Sequence, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

VENTA_ESTADOS = ("en_curso", "confirmada", "anulada")
TIPO_COMPROBANTE = ("factura", "nota_venta")

# Generador de venta_id para ventas nuevas del POS (ronda 7). Las ventas
# históricas del dataset conservan su basket_id original (máx. ~4.1e10).
venta_id_seq = Sequence("ventas_venta_id_seq", start=100_000_000_000)


class Venta(Base):
    """Mapea `ventas` tal como queda tras la extensión de la feature 001
    (`anulada` eliminada; `estado` es la única fuente de verdad del ciclo)."""

    __tablename__ = "ventas"

    venta_id: Mapped[int] = mapped_column(
        BigInteger, venta_id_seq, server_default=venta_id_seq.next_value(), primary_key=True
    )
    tienda_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cajero_id: Mapped[int] = mapped_column(Integer, nullable=False)
    household_id: Mapped[int | None] = mapped_column(Integer)
    medio_pago_id: Mapped[int | None] = mapped_column(Integer)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    semana: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="en_curso")
    tipo_comprobante: Mapped[str] = mapped_column(String(20), nullable=False, default="nota_venta")
    identificacion_comprador: Mapped[str] = mapped_column(
        String(13), nullable=False, default="9999999999999"
    )
    razon_social_comprador: Mapped[str] = mapped_column(
        String(150), nullable=False, default="CONSUMIDOR FINAL"
    )
    # Clave del PDF del comprobante en el bucket MinIO 'comprobantes-venta'
    # (ronda 7, FR-004). NULL mientras la venta no se ha confirmado.
    comprobante_objeto: Mapped[str | None] = mapped_column(String(300))
