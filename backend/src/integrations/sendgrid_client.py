"""Cliente SendGrid — correo transaccional (pedidos especiales, FR-029).

Scaffolding de la Fase 2. El envío real de la orden especial se implementa en T057.
El registro de negocio (`ordenes_compra.tipo='especial'`) NO depende de que el
correo se entregue (Principio II).
"""

from __future__ import annotations

import base64

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Attachment, Disposition, FileContent, FileName, FileType, Mail

from src.core.config import settings


def is_configured() -> bool:
    return bool(settings.sendgrid_api_key and settings.sendgrid_from_email)


def _client() -> SendGridAPIClient:
    return SendGridAPIClient(settings.sendgrid_api_key)


def enviar_correo(
    *,
    to: str,
    subject: str,
    html: str,
    adjunto_pdf: bytes | None = None,
    adjunto_nombre: str = "adjunto.pdf",
) -> bool:
    """Devuelve True si SendGrid aceptó el mensaje (2xx). Nunca lanza hacia el
    caller: un fallo del proveedor no debe abortar la operación de negocio."""
    if not is_configured():
        return False
    try:
        message = Mail(
            from_email=settings.sendgrid_from_email,
            to_emails=to,
            subject=subject,
            html_content=html,
        )
        if adjunto_pdf is not None:
            message.attachment = Attachment(
                FileContent(base64.b64encode(adjunto_pdf).decode()),
                FileName(adjunto_nombre),
                FileType("application/pdf"),
                Disposition("attachment"),
            )
        response = _client().send(message)
        return 200 <= response.status_code < 300
    except Exception:  # noqa: BLE001 - se degrada silenciosamente por diseño
        return False
