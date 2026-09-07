from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, Sequence, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

# Generador de household_id para altas nuevas (ronda 5). Los ~2500 hogares del
# dataset Dunnhumby conservan su household_id original.
household_id_seq = Sequence("clientes_household_id_seq", start=900_000)


class Cliente(Base):
    """`clientes` — maestro de cliente. `household_id` es la natural key del dataset
    Dunnhumby. `consentimiento_datos` (ronda 1) es el gate LOPDP: un cliente sin
    consentimiento nunca entra a CLV/churn/campañas (FR-001). `documento_identidad`
    (ronda 5) es la cédula/RUC opcional, única sólo cuando se proporciona.
    """

    __tablename__ = "clientes"

    household_id: Mapped[int] = mapped_column(
        Integer,
        household_id_seq,
        server_default=household_id_seq.next_value(),
        primary_key=True,
    )
    nombre: Mapped[str | None] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(150), unique=True)
    telefono: Mapped[str | None] = mapped_column(String(20))
    documento_identidad: Mapped[str | None] = mapped_column(String(13))
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date)
    fecha_registro: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    consentimiento_datos: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_consentimiento_datos: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
