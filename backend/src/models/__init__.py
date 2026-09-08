"""Modelos SQLAlchemy — fuente única de verdad del mapeo objeto-tabla
(Principio VIII: no se duplica por módulo). Cubre las tablas de las features
001 (ventas/inventario/compras/catálogo) y 002 (clientes/fidelización).

Las referencias a tablas de otras features (tiendas, empleados, fabricantes,
roles) se dejan como columnas `Integer`: su integridad la garantiza la FK real
en PostgreSQL (migración Alembic desde `01_operativo_postgres.sql`), no el ORM.
"""

from src.models.ajuste_inventario import AjusteInventario
from src.models.alerta_inventario import AlertaInventario
from src.models.anulacion_venta import AnulacionVenta
from src.models.apertura_caja import AperturaCaja
from src.models.cambio_clasificacion_abc import CambioClasificacionAbc
from src.models.campana import Campana
from src.models.campana_cliente import CampanaCliente
from src.models.campana_resultado import CampanaResultado
from src.models.candidato_liquidacion import CandidatoLiquidacion
from src.models.churn_score import ChurnScore
from src.models.cierre_caja import CierreCaja
from src.models.cliente import Cliente
from src.models.cliente_clv import ClienteClv
from src.models.cliente_demografico import ClienteDemografico
from src.models.competidor import Competidor
from src.models.configuracion_caja import ConfiguracionCaja
from src.models.configuracion_inventario import ConfiguracionInventario
from src.models.configuracion_pricing import ConfiguracionPricing
from src.models.configuracion_promociones import ConfiguracionPromociones
from src.models.configuracion_pronostico import ConfiguracionPronostico
from src.models.configuracion_seguridad_pagos import ConfiguracionSeguridadPagos
from src.models.cupon import Cupon
from src.models.cupon_enviado import CuponEnviado
from src.models.cupon_redimido import CuponRedimido
from src.models.datafono import Datafono
from src.models.devolucion import Devolucion
from src.models.evento_cliente import EventoCliente
from src.models.evento_quiebre_stock import EventoQuiebreStock
from src.models.factura_proveedor import FacturaProveedor
from src.models.historial_precio import HistorialPrecio
from src.models.incidente_fraude import IncidenteFraude
from src.models.incidente_seguridad_pago import IncidenteSeguridadPago
from src.models.intento_pago_tarjeta import IntentoPagoTarjeta
from src.models.inventario import Inventario
from src.models.linea_venta_removida import LineaVentaRemovida
from src.models.lote import Lote
from src.models.margen_objetivo import MargenObjetivo
from src.models.medio_pago import MedioPago
from src.models.merma import Merma
from src.models.modelo_demanda import ModeloDemanda
from src.models.monitoreo_precision_modelo import MonitoreoPrecisionModelo
from src.models.movimiento_inventario import MovimientoInventario
from src.models.nivel_fidelizacion import NivelFidelizacion
from src.models.orden_compra import OrdenCompra
from src.models.orden_compra_detalle import OrdenCompraDetalle
from src.models.pago_proveedor import PagoProveedor
from src.models.politica_seguridad_pagos import PoliticaSeguridadPagos
from src.models.precio_competencia import PrecioCompetencia
from src.models.producto import Producto
from src.models.pronostico_demanda import PronosticoDemanda
from src.models.propuesta_ajuste_precio import PropuestaAjustePrecio
from src.models.protocolo_escalamiento import ProtocoloEscalamiento
from src.models.proveedor import Proveedor
from src.models.recepcion_mercaderia import RecepcionMercaderia
from src.models.regla_afinidad import ReglaAfinidad
from src.models.revision_margen_bajo import RevisionMargenBajo
from src.models.stock_maximo_categoria import StockMaximoCategoria
from src.models.umbral_merma_categoria import UmbralMermaCategoria
from src.models.venta import Venta
from src.models.venta_detalle import VentaDetalle
from src.models.verificacion_anaquel import VerificacionAnaquel

__all__ = [
    "AjusteInventario",
    "AlertaInventario",
    "AnulacionVenta",
    "AperturaCaja",
    "CambioClasificacionAbc",
    "Campana",
    "CampanaCliente",
    "CampanaResultado",
    "CandidatoLiquidacion",
    "ChurnScore",
    "CierreCaja",
    "Cliente",
    "ClienteClv",
    "ClienteDemografico",
    "Competidor",
    "ConfiguracionCaja",
    "ConfiguracionInventario",
    "ConfiguracionPricing",
    "ConfiguracionPromociones",
    "ConfiguracionPronostico",
    "ConfiguracionSeguridadPagos",
    "Cupon",
    "CuponEnviado",
    "CuponRedimido",
    "Datafono",
    "Devolucion",
    "EventoCliente",
    "EventoQuiebreStock",
    "FacturaProveedor",
    "HistorialPrecio",
    "IncidenteFraude",
    "IncidenteSeguridadPago",
    "IntentoPagoTarjeta",
    "Inventario",
    "LineaVentaRemovida",
    "Lote",
    "MargenObjetivo",
    "MedioPago",
    "Merma",
    "ModeloDemanda",
    "MonitoreoPrecisionModelo",
    "MovimientoInventario",
    "NivelFidelizacion",
    "OrdenCompra",
    "OrdenCompraDetalle",
    "PagoProveedor",
    "PoliticaSeguridadPagos",
    "PrecioCompetencia",
    "Producto",
    "PronosticoDemanda",
    "PropuestaAjustePrecio",
    "ProtocoloEscalamiento",
    "Proveedor",
    "RecepcionMercaderia",
    "ReglaAfinidad",
    "RevisionMargenBajo",
    "StockMaximoCategoria",
    "UmbralMermaCategoria",
    "Venta",
    "VentaDetalle",
    "VerificacionAnaquel",
]
