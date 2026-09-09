from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from src.integrations import reportlab_invoice
from src.models.venta_detalle import VentaDetalle
from src.modules.ventas.service import calcular_desglose_venta


def test_calcular_desglose_venta_con_iva_15():
    # Línea 1: PVP $11.50 c/u, 2 unidades -> Total $23.00 (Neto $20.00, IVA $3.00)
    linea1 = VentaDetalle(
        venta_detalle_id=1,
        venta_id=100,
        product_id=101,
        cantidad=2,
        sales_value=Decimal("11.50"),
        retail_disc=Decimal("0.00"),
        coupon_disc=Decimal("0.00"),
    )
    desglose = calcular_desglose_venta([linea1], descuento_venta=Decimal("0.00"), tarifa_iva=Decimal("15.00"))

    assert desglose["subtotal_sin_impuestos"] == Decimal("20.00")
    assert desglose["subtotal_15"] == Decimal("20.00")
    assert desglose["iva_15"] == Decimal("3.00")
    assert desglose["total"] == Decimal("23.00")
    assert desglose["total_descuento"] == Decimal("0.00")


def test_calcular_desglose_venta_con_descuento():
    # Línea con PVP $11.50, 2 unidades ($23.00), descuento retail $2.30 -> Total $20.70 (Neto $18.00, IVA $2.70)
    linea = VentaDetalle(
        venta_detalle_id=1,
        venta_id=100,
        product_id=101,
        cantidad=2,
        sales_value=Decimal("11.50"),
        retail_disc=Decimal("2.30"),
        coupon_disc=Decimal("0.00"),
    )
    desglose = calcular_desglose_venta([linea], descuento_venta=Decimal("0.00"), tarifa_iva=Decimal("15.00"))

    assert desglose["subtotal_sin_impuestos"] == Decimal("18.00")
    assert desglose["total_descuento"] == Decimal("2.00")
    assert desglose["iva_15"] == Decimal("2.70")
    assert desglose["total"] == Decimal("20.70")


def test_clave_acceso_sri_49_digitos():
    fecha = datetime(2026, 9, 9, 14, 30, 0)
    clave = reportlab_invoice.generar_clave_acceso_sri(
        fecha=fecha,
        tipo_comprobante="factura",
        ruc="1792345678001",
        ambiente="2",
        serie="001001",
        secuencial=12345,
    )
    assert len(clave) == 49
    assert clave.isdigit()
    # Los primeros 8 dígitos son la fecha DDMMAAAA
    assert clave[:8] == "09092026"
    # Código comprobante factura: 01
    assert clave[8:10] == "01"


def test_render_pdf_sri_factura():
    datos = reportlab_invoice.DatosComprobante(
        venta_id=10000001,
        tienda="Tienda 1 - Centro Histórico",
        fecha_hora=datetime(2026, 9, 9, 14, 30, 0),
        tipo_comprobante="factura",
        identificacion_comprador="1712345678",
        razon_social_comprador="JUAN PEREZ",
        direccion_comprador="Av. 10 de Agosto",
        email_comprador="juan@ejemplo.com",
        lineas=[
            reportlab_invoice.LineaComprobante(
                codigo="101",
                descripcion="Leche Entera 1L",
                cantidad=2,
                precio_unitario=Decimal("1.00"),
                descuento=Decimal("0.00"),
                subtotal=Decimal("2.00"),
                tarifa_iva=Decimal("15.00"),
                iva_monto=Decimal("0.30"),
                pvp_unitario=Decimal("1.15"),
            )
        ],
        subtotal_15=Decimal("2.00"),
        subtotal_sin_impuestos=Decimal("2.00"),
        iva_15=Decimal("0.30"),
        tarifa_iva_pct=Decimal("15.00"),
        total=Decimal("2.30"),
    )
    pdf_bytes = reportlab_invoice.render_pdf(datos)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")
