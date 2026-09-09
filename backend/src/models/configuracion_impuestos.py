from __future__ import annotations

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

CLAVE_IVA_VIGENTE_PCT = "iva_porcentaje_vigente"
CLAVE_IVA_CODIGO_SRI = "iva_codigo_sri"


class ConfiguracionImpuestos(Base):
    """`configuracion_impuestos` — parámetros tributarios generales del sistema.

    Almacena la tarifa vigente de IVA (15% en Ecuador) y su código SRI.
    No es editable desde la interfaz gráfica de usuario (UI) por ser un dato
    fiscal sensible; cualquier modificación se realiza directamente en tabla
    a nivel de base de datos por personal autorizado.
    """

    __tablename__ = "configuracion_impuestos"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(250))
