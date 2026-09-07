from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ClienteDemografico(Base):
    """`clientes_demograficos` — atributos del dataset (bandas de texto, no numéricos)."""

    __tablename__ = "clientes_demograficos"

    household_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clientes.household_id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
    )
    age: Mapped[str | None] = mapped_column(String(20))
    income: Mapped[str | None] = mapped_column(String(20))
    home_ownership: Mapped[str | None] = mapped_column(String(20))
    marital_status: Mapped[str | None] = mapped_column(String(20))
    household_size: Mapped[str | None] = mapped_column(String(10))
    household_comp: Mapped[str | None] = mapped_column(String(30))
    kids_count: Mapped[str | None] = mapped_column(String(10))
