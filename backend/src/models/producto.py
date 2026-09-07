from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, Boolean, DateTime, Integer, Numeric, Sequence, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

# Generador de product_id para altas nuevas del catálogo (ronda 10). Las ~92k
# productos del dataset conservan su product_id original (máx. 18_316_298).
product_id_seq = Sequence("productos_product_id_seq", start=90_000_000)


class Producto(Base):
    __tablename__ = "productos"

    product_id: Mapped[int] = mapped_column(
        Integer, product_id_seq, server_default=product_id_seq.next_value(), primary_key=True
    )
    manufacturer_id: Mapped[int | None] = mapped_column(Integer)
    department: Mapped[str | None] = mapped_column(String(60))
    brand: Mapped[str | None] = mapped_column(String(20))
    nombre: Mapped[str | None] = mapped_column(String(200))  # ronda 10 (FR-013)
    marca: Mapped[str | None] = mapped_column(String(120))  # ronda 10 (FR-013)
    product_category: Mapped[str | None] = mapped_column(String(100))
    product_type: Mapped[str | None] = mapped_column(String(100))
    package_size: Mapped[str | None] = mapped_column(String(30))
    costo: Mapped[float | None] = mapped_column(Numeric(10, 2))
    precio_base: Mapped[float | None] = mapped_column(Numeric(10, 2))
    es_perecedero: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vida_util_dias: Mapped[int | None] = mapped_column(Integer)
    clasificacion_abc: Mapped[str | None] = mapped_column(CHAR(1))
    es_ancla: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    codigo_barras: Mapped[str | None] = mapped_column(String(20), unique=True)
    imagen_url: Mapped[str | None] = mapped_column(String(500))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
