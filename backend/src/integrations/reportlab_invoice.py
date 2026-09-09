"""Comprobante de venta en PDF (FR-004) + subida a MinIO (research.md §7).

`reportlab` arma el PDF server-side al confirmar la venta; se guarda tal cual se
emitió en el bucket `comprobantes-venta` (Principio III) y se sirve luego vía
endpoint autenticado con `Content-Disposition: inline`.
"""

from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import urllib3
from minio import Minio
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from src.core.config import settings

# reportlab necesita un raster (PNG/JPG), no SVG (research.md §7).
LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "branding" / "logo.png"
_EMPRESA = "Marzú Retail Group"


@dataclass(slots=True)
class LineaComprobante:
    descripcion: str
    cantidad: int
    precio_unitario: Decimal

    @property
    def subtotal(self) -> Decimal:
        return self.precio_unitario * self.cantidad


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


def minio_client() -> Minio:
    # Falla rápido: si MinIO no está, el comprobante se re-renderiza al vuelo y no
    # se debe hacer esperar al cajero (Principio II). Sin reintentos, timeout corto.
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
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 25 * mm

    if LOGO_PATH.exists():
        # El logo es decorativo: si falla el raster, el comprobante igual se emite.
        with contextlib.suppress(Exception):
            c.drawImage(
                str(LOGO_PATH),
                20 * mm,
                y - 5 * mm,
                width=35 * mm,
                height=18 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )

    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(width - 20 * mm, y, _EMPRESA)
    c.setFont("Helvetica", 10)
    etiqueta = "FACTURA" if datos.tipo_comprobante == "factura" else "NOTA DE VENTA"
    c.drawRightString(width - 20 * mm, y - 6 * mm, f"{etiqueta} N° {datos.venta_id}")
    c.drawRightString(width - 20 * mm, y - 11 * mm, datos.fecha_hora.strftime("%Y-%m-%d %H:%M"))

    y -= 28 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Tienda: {datos.tienda}")
    y -= 5 * mm
    c.drawString(20 * mm, y, f"Cliente: {datos.razon_social_comprador}")
    y -= 5 * mm
    c.drawString(20 * mm, y, f"Identificación: {datos.identificacion_comprador}")

    y -= 12 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20 * mm, y, "Descripción")
    c.drawRightString(120 * mm, y, "Cant.")
    c.drawRightString(150 * mm, y, "P. Unit.")
    c.drawRightString(width - 20 * mm, y, "Subtotal")
    y -= 2 * mm
    c.line(20 * mm, y, width - 20 * mm, y)
    y -= 6 * mm

    c.setFont("Helvetica", 9)
    for linea in datos.lineas:
        c.drawString(20 * mm, y, linea.descripcion[:60])
        c.drawRightString(120 * mm, y, str(linea.cantidad))
        c.drawRightString(150 * mm, y, f"{linea.precio_unitario:.2f}")
        c.drawRightString(width - 20 * mm, y, f"{linea.subtotal:.2f}")
        y -= 6 * mm
        if y < 30 * mm:
            c.showPage()
            y = height - 25 * mm
            c.setFont("Helvetica", 9)

    y -= 2 * mm
    c.line(110 * mm, y, width - 20 * mm, y)
    y -= 7 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(150 * mm, y, "TOTAL")
    c.drawRightString(width - 20 * mm, y, f"{datos.total:.2f}")

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
