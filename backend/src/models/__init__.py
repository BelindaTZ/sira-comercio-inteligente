"""Modelos SQLAlchemy — fuente única de verdad del mapeo objeto-tabla
(Principio VIII: no se duplica por módulo). Cubre las tablas de las features
001 (ventas/inventario/compras/catálogo) y 002 (clientes/fidelización).

Las referencias a tablas de otras features (tiendas, empleados, fabricantes,
roles) se dejan como columnas `Integer`: su integridad la garantiza la FK real
en PostgreSQL (migración Alembic desde `01_operativo_postgres.sql`), no el ORM.
"""

from src.models.accion_retencion import AccionRetencion
from src.models.ajuste_inventario import AjusteInventario
from src.models.alerta_inventario import AlertaInventario
from src.models.anulacion_venta import AnulacionVenta
from src.models.apertura_caja import AperturaCaja
from src.models.cambio_clasificacion_abc import CambioClasificacionAbc
from src.models.campana import Campana
from src.models.campana_cliente import CampanaCliente
from src.models.campana_resultado import CampanaResultado
from src.models.candidato_liquidacion import CandidatoLiquidacion
from src.models.capacitacion import Capacitacion
from src.models.churn_score import ChurnScore
from src.models.cierre_caja import CierreCaja
from src.models.cliente import Cliente
from src.models.cliente_clv import ClienteClv
from src.models.cliente_demografico import ClienteDemografico
from src.models.clima_laboral import ClimaLaboral
from src.models.competidor import Competidor
from src.models.configuracion_caja import ConfiguracionCaja
from src.models.configuracion_impuestos import ConfiguracionImpuestos
from src.models.configuracion_inventario import ConfiguracionInventario
from src.models.configuracion_pricing import ConfiguracionPricing
from src.models.configuracion_promociones import ConfiguracionPromociones
from src.models.configuracion_pronostico import ConfiguracionPronostico
from src.models.configuracion_seguridad_pagos import ConfiguracionSeguridadPagos
from src.models.corrida_carga import CorridaCarga
from src.models.cupon import Cupon
from src.models.cupon_enviado import CuponEnviado
from src.models.cupon_redimido import CuponRedimido
from src.models.dashboard_kpi import DashboardKpi
from src.models.dashboard_operativo_estado import DashboardOperativoEstado
from src.models.datafono import Datafono
from src.models.devolucion import Devolucion
from src.models.empleado import Empleado
from src.models.empleado_capacitacion import EmpleadoCapacitacion
from src.models.evento_cliente import EventoCliente
from src.models.evento_quiebre_stock import EventoQuiebreStock
from src.models.factura_proveedor import FacturaProveedor
from src.models.historial_precio import HistorialPrecio
from src.models.incidente_fraude import IncidenteFraude
from src.models.incidente_seguridad_pago import IncidenteSeguridadPago
from src.models.intento_login import IntentoLogin
from src.models.intento_pago_tarjeta import IntentoPagoTarjeta
from src.models.inventario import Inventario
from src.models.linea_venta_removida import LineaVentaRemovida
from src.models.lote import Lote
from src.models.margen_objetivo import MargenObjetivo
from src.models.medio_pago import MedioPago
from src.models.merma import Merma
from src.models.modelo_datos_warehouse import ModeloDatosWarehouse
from src.models.modelo_demanda import ModeloDemanda
from src.models.monitoreo_precision_modelo import MonitoreoPrecisionModelo
from src.models.movimiento_inventario import MovimientoInventario
from src.models.nivel_fidelizacion import NivelFidelizacion
from src.models.orden_compra import OrdenCompra
from src.models.orden_compra_detalle import OrdenCompraDetalle
from src.models.pago_proveedor import PagoProveedor
from src.models.plan_sucesion import PlanSucesion
from src.models.politica_gobierno_datos import PoliticaGobiernoDatos
from src.models.politica_seguridad_pagos import PoliticaSeguridadPagos
from src.models.precio_competencia import PrecioCompetencia
from src.models.producto import Producto
from src.models.pronostico_demanda import PronosticoDemanda
from src.models.propuesta_ajuste_precio import PropuestaAjustePrecio
from src.models.protocolo_escalamiento import ProtocoloEscalamiento
from src.models.proveedor import Proveedor
from src.models.recepcion_mercaderia import RecepcionMercaderia
from src.models.recuperacion_password import RecuperacionPassword
from src.models.registro_calidad_carga import RegistroCalidadCarga
from src.models.registro_publicacion_dashboard import RegistroPublicacionDashboard
from src.models.regla_afinidad import ReglaAfinidad
from src.models.revision_margen_bajo import RevisionMargenBajo
from src.models.rol_puesto import RolPuesto
from src.models.role_permiso import RolePermisoModulo, RolePermisoTabla
from src.models.stock_maximo_categoria import StockMaximoCategoria
from src.models.traslado_stock import TrasladoStock
from src.models.umbral_merma_categoria import UmbralMermaCategoria
from src.models.usuario import Usuario
from src.models.venta import Venta
from src.models.venta_detalle import VentaDetalle
from src.models.verificacion_anaquel import VerificacionAnaquel

__all__ = [
    "AccionRetencion",
    "AjusteInventario",
    "AlertaInventario",
    "AnulacionVenta",
    "AperturaCaja",
    "CambioClasificacionAbc",
    "Campana",
    "CampanaCliente",
    "CampanaResultado",
    "CandidatoLiquidacion",
    "Capacitacion",
    "ChurnScore",
    "CierreCaja",
    "ClimaLaboral",
    "Cliente",
    "ClienteClv",
    "ClienteDemografico",
    "Competidor",
    "ConfiguracionCaja",
    "ConfiguracionImpuestos",
    "ConfiguracionInventario",
    "ConfiguracionPricing",
    "ConfiguracionPromociones",
    "ConfiguracionPronostico",
    "ConfiguracionSeguridadPagos",
    "CorridaCarga",
    "Cupon",
    "CuponEnviado",
    "CuponRedimido",
    "DashboardKpi",
    "DashboardOperativoEstado",
    "Datafono",
    "Devolucion",
    "Empleado",
    "EmpleadoCapacitacion",
    "EventoCliente",
    "EventoQuiebreStock",
    "FacturaProveedor",
    "HistorialPrecio",
    "IncidenteFraude",
    "IncidenteSeguridadPago",
    "IntentoLogin",
    "IntentoPagoTarjeta",
    "Inventario",
    "LineaVentaRemovida",
    "Lote",
    "MargenObjetivo",
    "MedioPago",
    "Merma",
    "ModeloDatosWarehouse",
    "ModeloDemanda",
    "MonitoreoPrecisionModelo",
    "MovimientoInventario",
    "NivelFidelizacion",
    "OrdenCompra",
    "OrdenCompraDetalle",
    "PagoProveedor",
    "PlanSucesion",
    "PoliticaGobiernoDatos",
    "PoliticaSeguridadPagos",
    "PrecioCompetencia",
    "Producto",
    "PronosticoDemanda",
    "PropuestaAjustePrecio",
    "ProtocoloEscalamiento",
    "Proveedor",
    "RecepcionMercaderia",
    "RecuperacionPassword",
    "RegistroCalidadCarga",
    "RegistroPublicacionDashboard",
    "ReglaAfinidad",
    "RevisionMargenBajo",
    "RolPuesto",
    "RolePermisoModulo",
    "RolePermisoTabla",
    "StockMaximoCategoria",
    "TrasladoStock",
    "UmbralMermaCategoria",
    "Usuario",
    "Venta",
    "VentaDetalle",
    "VerificacionAnaquel",
]
