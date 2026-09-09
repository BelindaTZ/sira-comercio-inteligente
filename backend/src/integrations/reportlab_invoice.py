"""Comprobante de venta en PDF — Estándar RIDE / Facturación Electrónica SRI Ecuador.

Genera la Representación Impresa del Documento Electrónico (RIDE) cumpliendo
con todos los requisitos reglamentarios del SRI:
- Cabecera con datos del emisor (RUC, Razón social, Matriz, Sucursal, Obligado a llevar contabilidad).
- Bloque de autorización con clave de acceso de 49 dígitos y código de barras Code 128.
- Datos del comprador / receptor (Razón social, RUC/Cédula, Dirección, Email, Teléfono).
- Detalle de ítems con precio unitario neto sin impuestos, descuentos y precio total sin impuestos.
- Desglose oficial de impuestos SRI: Subtotal gravado (15%), Subtotal 0%, Subtotal no objeto,
  Subtotal exento, Subtotal sin impuestos, Total Descuento, IVA 15% y Valor Total.
- Sección de Formas de Pago e Información Adicional.
"""

from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import urllib3
from minio import Minio
from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from src.core.config import settings

LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "branding" / "logo.png"

# Datos corporativos emisores Marzú Retail Group (Ecuador)
EMPRESA_RAZON_SOCIAL = "Marzú Retail Group S.A."
EMPRESA_NOMBRE_COMERCIAL = "Marzú Supermercados"
EMPRESA_RUC = "1792345678001"
EMPRESA_MATRIZ = "Av. Amazonas N24-196 y Luis Cordero, Quito - Ecuador"
EMPRESA_OBLIGADO_CONTABILIDAD = "SÍ"
EMPRESA_CONTRIBUYENTE_ESPECIAL = "Resolución NAC-00432"


def calcular_digito_modulo11(cadena48: str) -> str:
    """Calcula el dígito verificador módulo 11 ponderado según el estándar SRI Ecuador."""
    pesos = [2, 3, 4, 5, 6, 7]
    suma = sum(int(ch) * pesos[i % 6] for i, ch in enumerate(reversed(cadena48)))
    residuo = suma % 11
    resultado = 11 - residuo
    if resultado == 11:
        return "0"
    if resultado == 10:
        return "1"
    return str(resultado)


def generar_clave_acceso_sri(
    fecha: datetime,
    tipo_comprobante: str,
    ruc: str,
    ambiente: str,
    serie: str,
    secuencial: int,
) -> str:
    """Genera la clave de acceso de 49 dígitos requerida por el SRI."""
    fecha_str = fecha.strftime("%d%m%Y")
    tipo_cod = "01" if tipo_comprobante == "factura" else "02"
    ruc_pad = ruc.replace("-", "").strip()[:13].zfill(13)
    amb_cod = "2" if ambiente.lower() in ("produccion", "producción", "2") else "1"
    serie_cod = "".join(c for c in serie if c.isdigit())[:6].zfill(6)
    sec_cod = f"{secuencial % 1_000_000_000:09d}"
    codigo_num = f"{(secuencial * 7919) % 100_000_000:08d}"
    tipo_emision = "1"  # Emisión normal

    base48 = f"{fecha_str}{tipo_cod}{ruc_pad}{amb_cod}{serie_cod}{sec_cod}{codigo_num}{tipo_emision}"
    dv = calcular_digito_modulo11(base48)
    return f"{base48}{dv}"


@dataclass(slots=True)
class LineaComprobante:
    codigo: str
    descripcion: str
    cantidad: int
    precio_unitario: Decimal  # Precio neto sin IVA
    descuento: Decimal = Decimal("0.00")  # Descuento neto sin IVA
    subtotal: Decimal = Decimal("0.00")  # (precio_unitario * cantidad) - descuento
    tarifa_iva: Decimal = Decimal("15.00")
    iva_monto: Decimal = Decimal("0.00")
    pvp_unitario: Decimal = Decimal("0.00")  # Precio con IVA para referencia


@dataclass(slots=True)
class DatosComprobante:
    venta_id: int
    tienda: str
    fecha_hora: datetime
    tipo_comprobante: str
    identificacion_comprador: str
    razon_social_comprador: str
    lineas: list[LineaComprobante]
    total: Decimal
    direccion_comprador: str = "S/N"
    email_comprador: str = ""
    telefono_comprador: str = ""
    forma_pago: str = "01 - SIN UTILIZACION DEL SISTEMA FINANCIERO"
    # Totales y subtotales SRI
    subtotal_15: Decimal = Decimal("0.00")
    subtotal_0: Decimal = Decimal("0.00")
    subtotal_no_objeto: Decimal = Decimal("0.00")
    subtotal_exento: Decimal = Decimal("0.00")
    subtotal_sin_impuestos: Decimal = Decimal("0.00")
    total_descuento: Decimal = Decimal("0.00")
    iva_15: Decimal = Decimal("0.00")
    tarifa_iva_pct: Decimal = Decimal("15.00")
    propina: Decimal = Decimal("0.00")
    # Metadatos del emisor
    numero_factura: str = ""
    clave_acceso: str = ""
    cajero_nombre: str = ""


def minio_client() -> Minio:
    http_client = urllib3.PoolManager(
        timeout=urllib3.Timeout(connect=2.0, read=4.0),
        retries=urllib3.Retry(total=0),
    )
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        http_client=http_client,
    )


def ensure_bucket(name: str) -> None:
    client = minio_client()
    if not client.bucket_exists(name):
        client.make_bucket(name)


def render_pdf(datos: DatosComprobante) -> bytes:
    """Renderiza el documento electrónico (RIDE) de Factura o Nota de Venta conforme a la normativa SRI."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    margen_x = 10 * mm
    ancho_util = width - (2 * margen_x)

    # Clave de acceso y número de factura si no vienen predefinidos
    num_factura = datos.numero_factura or f"001-001-{datos.venta_id % 1_000_000_000:09d}"
    clave_acceso = datos.clave_acceso or generar_clave_acceso_sri(
        fecha=datos.fecha_hora,
        tipo_comprobante=datos.tipo_comprobante,
        ruc=EMPRESA_RUC,
        ambiente="2",
        serie="001001",
        secuencial=datos.venta_id,
    )

    y = height - 10 * mm

    # =========================================================================
    # 1. CABECERA: 2 COLUMNAS (Emisor izquierda | Autorización SRI derecha)
    # =========================================================================
    ancho_col1 = 92 * mm
    ancho_col2 = 94 * mm
    x_col2 = margen_x + ancho_col1 + 4 * mm
    alto_cajas = 64 * mm
    top_cajas = y - alto_cajas

    # Caja Izquierda: Emisor
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.8)
    c.roundRect(margen_x, top_cajas, ancho_col1, alto_cajas, 3 * mm, stroke=1, fill=0)

    # Logo
    if LOGO_PATH.exists():
        with contextlib.suppress(Exception):
            c.drawImage(
                str(LOGO_PATH),
                margen_x + 4 * mm,
                y - 18 * mm,
                width=35 * mm,
                height=14 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margen_x + 4 * mm, y - 23 * mm, EMPRESA_RAZON_SOCIAL)
    c.setFont("Helvetica", 8)
    c.drawString(margen_x + 4 * mm, y - 28 * mm, f"Nombre Comercial: {EMPRESA_NOMBRE_COMERCIAL}")
    c.drawString(margen_x + 4 * mm, y - 33 * mm, f"Matriz: {EMPRESA_MATRIZ[:55]}")
    c.drawString(margen_x + 4 * mm, y - 38 * mm, f"Sucursal: {datos.tienda}")
    c.drawString(margen_x + 4 * mm, y - 43 * mm, f"Contribuyente Especial Nro: {EMPRESA_CONTRIBUYENTE_ESPECIAL}")
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margen_x + 4 * mm, y - 48 * mm, f"OBLIGADO A LLEVAR CONTABILIDAD: {EMPRESA_OBLIGADO_CONTABILIDAD}")

    # Caja Derecha: Autorización SRI / Clave de Acceso
    c.roundRect(x_col2, top_cajas, ancho_col2, alto_cajas, 3 * mm, stroke=1, fill=0)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_col2 + 4 * mm, y - 6 * mm, f"R.U.C.: {EMPRESA_RUC}")
    c.setFont("Helvetica-Bold", 11)
    etiqueta = "FACTURA" if datos.tipo_comprobante == "factura" else "NOTA DE VENTA"
    c.drawString(x_col2 + 4 * mm, y - 11 * mm, etiqueta)
    c.setFont("Helvetica", 9)
    c.drawString(x_col2 + 4 * mm, y - 16 * mm, f"No. {num_factura}")
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x_col2 + 4 * mm, y - 21 * mm, "NÚMERO DE AUTORIZACIÓN:")
    c.setFont("Helvetica", 6.5)
    c.drawString(x_col2 + 4 * mm, y - 25 * mm, clave_acceso)
    c.setFont("Helvetica", 7.5)
    c.drawString(
        x_col2 + 4 * mm,
        y - 30 * mm,
        f"FECHA Y HORA: {datos.fecha_hora.strftime('%d/%m/%Y %H:%M:%S')}",
    )
    c.drawString(x_col2 + 4 * mm, y - 34 * mm, "AMBIENTE: PRODUCCIÓN   EMISIÓN: NORMAL")

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x_col2 + 4 * mm, y - 39 * mm, "CLAVE DE ACCESO:")

    # Código de barras Code 128 con la clave de acceso oficial
    with contextlib.suppress(Exception):
        barcode = code128.Code128(clave_acceso, barWidth=0.23 * mm, barHeight=11 * mm)
        barcode.drawOn(c, x_col2 + 4 * mm, y - 53 * mm)

    c.setFont("Courier", 6.5)
    c.drawCentredString(x_col2 + (ancho_col2 / 2), y - 58 * mm, clave_acceso)

    # =========================================================================
    # 2. DATOS DEL CLIENTE / RECEPTOR
    # =========================================================================
    y = top_cajas - 3 * mm
    alto_receptor = 18 * mm
    c.roundRect(margen_x, y - alto_receptor, ancho_util, alto_receptor, 2 * mm, stroke=1, fill=0)

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(margen_x + 3 * mm, y - 5 * mm, "Razón Social / Nombres y Apellidos:")
    c.setFont("Helvetica", 7.5)
    c.drawString(margen_x + 52 * mm, y - 5 * mm, datos.razon_social_comprador[:50])

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(margen_x + 130 * mm, y - 5 * mm, "Identificación:")
    c.setFont("Helvetica", 7.5)
    c.drawString(margen_x + 152 * mm, y - 5 * mm, datos.identificacion_comprador)

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(margen_x + 3 * mm, y - 10 * mm, "Fecha Emisión:")
    c.setFont("Helvetica", 7.5)
    c.drawString(margen_x + 25 * mm, y - 10 * mm, datos.fecha_hora.strftime("%d/%m/%Y"))

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(margen_x + 65 * mm, y - 10 * mm, "Guía Remisión:")
    c.setFont("Helvetica", 7.5)
    c.drawString(margen_x + 88 * mm, y - 10 * mm, "S/G")

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(margen_x + 130 * mm, y - 10 * mm, "Dirección:")
    c.setFont("Helvetica", 7.5)
    c.drawString(margen_x + 146 * mm, y - 10 * mm, (datos.direccion_comprador or "S/N")[:26])

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(margen_x + 3 * mm, y - 15 * mm, "Email:")
    c.setFont("Helvetica", 7.5)
    c.drawString(margen_x + 15 * mm, y - 15 * mm, (datos.email_comprador or "consumidor@final.ec")[:40])

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(margen_x + 130 * mm, y - 15 * mm, "Teléfono:")
    c.setFont("Helvetica", 7.5)
    c.drawString(margen_x + 146 * mm, y - 15 * mm, (datos.telefono_comprador or "N/A")[:20])

    # =========================================================================
    # 3. TABLA DE DETALLE DE ÍTEMS
    # =========================================================================
    y -= (alto_receptor + 3 * mm)
    alto_fila_header = 5 * mm

    c.setFillColor(colors.HexColor("#1E293B"))
    c.rect(margen_x, y - alto_fila_header, ancho_util, alto_fila_header, stroke=0, fill=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7)
    # Columnas: Cod (20mm), Cant (12mm), Descripción (58mm), PVP (+IVA) (25mm), P.Unit sin IVA (25mm), Descuento (24mm), Total sin IVA (26mm) = 190mm
    c.drawString(margen_x + 2 * mm, y - 3.5 * mm, "Cod. Principal")
    c.drawRightString(margen_x + 28 * mm, y - 3.5 * mm, "Cant.")
    c.drawString(margen_x + 32 * mm, y - 3.5 * mm, "Descripción")
    c.drawRightString(margen_x + 115 * mm, y - 3.5 * mm, "PVP Unit. (+IVA)")
    c.drawRightString(margen_x + 140 * mm, y - 3.5 * mm, "P. Unit. (sin IVA)")
    c.drawRightString(margen_x + 164 * mm, y - 3.5 * mm, "Descuento")
    c.drawRightString(margen_x + ancho_util - 2 * mm, y - 3.5 * mm, "Precio Total")

    y -= alto_fila_header
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica", 7)

    for linea in datos.lineas:
        y -= 4.5 * mm
        c.drawString(margen_x + 2 * mm, y, str(linea.codigo)[:10])
        c.drawRightString(margen_x + 28 * mm, y, str(linea.cantidad))
        c.drawString(margen_x + 32 * mm, y, linea.descripcion[:38])
        c.drawRightString(margen_x + 115 * mm, y, f"${linea.pvp_unitario:.2f}")
        c.drawRightString(margen_x + 140 * mm, y, f"${linea.precio_unitario:.2f}")
        c.drawRightString(margen_x + 164 * mm, y, f"${linea.descuento:.2f}")
        c.drawRightString(margen_x + ancho_util - 2 * mm, y, f"${linea.subtotal:.2f}")

        c.setStrokeColor(colors.HexColor("#F1F5F9"))
        c.setLineWidth(0.4)
        c.line(margen_x, y - 1 * mm, margen_x + ancho_util, y - 1 * mm)

        if y < 75 * mm:
            c.showPage()
            y = height - 20 * mm
            c.setFont("Helvetica", 7)

    # =========================================================================
    # 4. PIE: INFORMACIÓN ADICIONAL + FORMAS DE PAGO (izq) | TOTALES SRI (der)
    # =========================================================================
    y_totales = max(y - 6 * mm, 65 * mm)
    ancho_info = 100 * mm
    ancho_tot = 86 * mm
    x_tot = margen_x + ancho_info + 4 * mm

    # Bloque Izquierdo: Información Adicional y Formas de Pago
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.8)
    c.roundRect(margen_x, y_totales - 48 * mm, ancho_info, 48 * mm, 2 * mm, stroke=1, fill=0)

    c.setFillColor(colors.HexColor("#1E293B"))
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(margen_x + 3 * mm, y_totales - 5 * mm, "INFORMACIÓN ADICIONAL")
    c.setFont("Helvetica", 7)
    c.drawString(margen_x + 3 * mm, y_totales - 9.5 * mm, f"Tienda: {datos.tienda}")
    c.drawString(margen_x + 3 * mm, y_totales - 13.5 * mm, f"Caja / Turno: Venta POS #{datos.venta_id}")
    c.drawString(
        margen_x + 3 * mm,
        y_totales - 17.5 * mm,
        f"Email cliente: {datos.email_comprador or 'consumidor@final.ec'}",
    )
    c.drawString(
        margen_x + 3 * mm,
        y_totales - 21.5 * mm,
        "Normativa: Comprobante Electrónico emitido bajo legislación SRI Ecuador.",
    )

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(margen_x + 3 * mm, y_totales - 28 * mm, "FORMA DE PAGO")
    c.rect(margen_x + 3 * mm, y_totales - 34 * mm, ancho_info - 6 * mm, 4 * mm, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(margen_x + 4 * mm, y_totales - 32.5 * mm, "Forma de Pago")
    c.drawRightString(margen_x + 65 * mm, y_totales - 32.5 * mm, "Total")
    c.drawRightString(margen_x + 80 * mm, y_totales - 32.5 * mm, "Plazo")
    c.drawRightString(margen_x + ancho_info - 4 * mm, y_totales - 32.5 * mm, "Tiempo")

    c.setFont("Helvetica", 6.5)
    c.drawString(margen_x + 4 * mm, y_totales - 38 * mm, datos.forma_pago[:38])
    c.drawRightString(margen_x + 65 * mm, y_totales - 38 * mm, f"${datos.total:.2f}")
    c.drawRightString(margen_x + 80 * mm, y_totales - 38 * mm, "0")
    c.drawRightString(margen_x + ancho_info - 4 * mm, y_totales - 38 * mm, "días")

    # Bloque Derecho: Cuadro de Totales Oficial SRI
    c.roundRect(x_tot, y_totales - 48 * mm, ancho_tot, 48 * mm, 2 * mm, stroke=1, fill=0)

    tarifa_iva_txt = f"{datos.tarifa_iva_pct:.0f}" if datos.tarifa_iva_pct % 1 == 0 else f"{datos.tarifa_iva_pct:.2f}"
    filas_totales = [
        (f"SUBTOTAL {tarifa_iva_txt}%", f"{datos.subtotal_15:.2f}", False),
        ("SUBTOTAL 0%", f"{datos.subtotal_0:.2f}", False),
        ("SUBTOTAL NO OBJETO DE IVA", f"{datos.subtotal_no_objeto:.2f}", False),
        ("SUBTOTAL EXENTO DE IVA", f"{datos.subtotal_exento:.2f}", False),
        ("SUBTOTAL SIN IMPUESTOS", f"{datos.subtotal_sin_impuestos:.2f}", True),
        ("TOTAL DESCUENTO", f"{datos.total_descuento:.2f}", False),
        (f"IVA {tarifa_iva_txt}%", f"{datos.iva_15:.2f}", True),
        ("PROPINA", f"{datos.propina:.2f}", False),
        ("VALOR TOTAL", f"{datos.total:.2f}", True),
    ]

    yt = y_totales - 4 * mm
    for etiqueta_tot, valor_tot, es_bold in filas_totales:
        c.setFont("Helvetica-Bold" if es_bold else "Helvetica", 7.5 if not es_bold else 8)
        if etiqueta_tot == "VALOR TOTAL":
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(colors.HexColor("#0F172A"))
        c.drawString(x_tot + 3 * mm, yt, etiqueta_tot)
        c.drawRightString(x_tot + ancho_tot - 3 * mm, yt, f"${valor_tot}")
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.setLineWidth(0.3)
        c.line(x_tot + 2 * mm, yt - 1 * mm, x_tot + ancho_tot - 2 * mm, yt - 1 * mm)
        yt -= 5.2 * mm

    c.showPage()
    c.save()
    return buf.getvalue()


def generar_y_subir_comprobante(datos: DatosComprobante) -> str:
    """Renderiza el PDF, lo sube a `comprobantes-venta` y devuelve la key del objeto."""
    pdf = render_pdf(datos)
    bucket = settings.minio_bucket_comprobantes
    key = f"{datos.fecha_hora:%Y/%m}/venta-{datos.venta_id}.pdf"

    ensure_bucket(bucket)
    minio_client().put_object(
        bucket,
        key,
        io.BytesIO(pdf),
        length=len(pdf),
        content_type="application/pdf",
    )
    return key


def descargar_comprobante(key: str) -> bytes:
    resp = minio_client().get_object(settings.minio_bucket_comprobantes, key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()
