from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

GRUPO_CAMPANA = ("tratado", "control")


class CampanaCliente(Base):
    """`campana_cliente` — asignación cliente↔campaña. `grupo` (ronda 2, feature
    002): en una campaña de reactivación cada cliente elegible es `tratado` o
    `control` — el uplift se mide comparando el retorno de ambos grupos (FR-016)."""

    __tablename__ = "campana_cliente"

    campaign_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("campanas.campaign_id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
    )
    household_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clientes.household_id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
    )
    grupo: Mapped[str | None] = mapped_column(String(20))
