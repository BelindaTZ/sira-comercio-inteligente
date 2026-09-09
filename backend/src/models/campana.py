from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, Sequence, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

CATEGORIA_SIRA = ("hito", "reactivacion", "afinidad")

# Campañas creadas por SIRA arrancan en 100000 (las del dataset Dunnhumby van por
# debajo de ese valor).
campana_id_seq = Sequence("campanas_campaign_id_seq", start=100000)


class Campana(Base):
    """`campanas` — `categoria_sira` (ronda 2, feature 002) marca las campañas
    propias de SIRA: `hito` (cumpleaños/aniversario) o `reactivacion` (con grupo
    de control obligatorio). NULL = campaña histórica del dataset."""

    __tablename__ = "campanas"

    campaign_id: Mapped[int] = mapped_column(
        Integer,
        campana_id_seq,
        server_default=campana_id_seq.next_value(),
        primary_key=True,
        autoincrement=False,
    )
    campaign_type: Mapped[str | None] = mapped_column(String(20))
    categoria_sira: Mapped[str | None] = mapped_column(String(20))
    nombre: Mapped[str | None] = mapped_column(String(120))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
