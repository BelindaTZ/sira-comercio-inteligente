"""Modelos SQLAlchemy — uno por tabla que toca la feature 001 (T009).

Fuente única de verdad del mapeo objeto-tabla (Principio VIII: no se duplica por
módulo). Las referencias a tablas de otras features (tiendas, empleados, clientes,
fabricantes, roles, medios_pago histórico) se dejan como columnas `Integer`: su
integridad la garantiza la FK real en PostgreSQL (migración de Alembic desde
`01_operativo_postgres.sql`), no el ORM.
"""

from src.models.ajuste_inventario import AjusteInventario
from src.models.alerta_inventario import AlertaInventario
from src.models.anulacion_venta import AnulacionVenta
from src.models.configuracion_inventario import ConfiguracionInventario
from src.models.devolucion import Devolucion
from src.models.evento_quiebre_stock import EventoQuiebreStock
from src.models.factura_proveedor import FacturaProveedor
from src.models.intento_pago_tarjeta import IntentoPagoTarjeta
from src.models.inventario import Inventario
from src.models.linea_venta_removida import LineaVentaRemovida
from src.models.lote import Lote
from src.models.medio_pago import MedioPago
from src.models.merma import Merma
from src.models.movimiento_inventario import MovimientoInventario
from src.models.orden_compra import OrdenCompra
from src.models.orden_compra_detalle import OrdenCompraDetalle
from src.models.pago_proveedor import PagoProveedor
from src.models.producto import Producto
from src.models.proveedor import Proveedor
from src.models.recepcion_mercaderia import RecepcionMercaderia
from src.models.stock_maximo_categoria import StockMaximoCategoria
from src.models.venta import Venta
from src.models.venta_detalle import VentaDetalle
from src.models.verificacion_anaquel import VerificacionAnaquel

__all__ = [
    "AjusteInventario",
    "AlertaInventario",
    "AnulacionVenta",
    "ConfiguracionInventario",
    "Devolucion",
    "EventoQuiebreStock",
    "FacturaProveedor",
    "IntentoPagoTarjeta",
    "Inventario",
    "LineaVentaRemovida",
    "Lote",
    "MedioPago",
    "Merma",
    "MovimientoInventario",
    "OrdenCompra",
    "OrdenCompraDetalle",
    "PagoProveedor",
    "Producto",
    "Proveedor",
    "RecepcionMercaderia",
    "StockMaximoCategoria",
    "Venta",
    "VentaDetalle",
    "VerificacionAnaquel",
]
