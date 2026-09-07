"""Cliente Stripe — Payment Intents en modo test (research.md #6, FR-030).

Los 3 resultados de FR-030 se obtienen con **PaymentMethods de prueba oficiales**
de Stripe, no con una simulación inventada:

- `aprobado`      → `pm_card_visa`                 → PaymentIntent `succeeded`
- `rechazado`     → `pm_card_visa_chargeDeclined`  → Stripe lanza `CardError`
- `error_tecnico` → no se contacta la pasarela      → se distingue de un rechazo
  del banco (research.md: "no pudimos ni preguntarle al banco")

El cajero nunca ve ni envía un PAN: el backend usa un token simbólico. Si no hay
`STRIPE_SECRET_KEY` configurada, se cae a un modo stub determinístico para que la
demo y los tests funcionen sin red.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import stripe

from src.core.config import settings

stripe.api_key = settings.stripe_secret_key

ResultadoPago = Literal["aprobado", "rechazado", "error_tecnico"]
Escenario = Literal["aprobado", "rechazado", "error_tecnico"]

_PM_POR_ESCENARIO: dict[Escenario, str] = {
    "aprobado": "pm_card_visa",
    "rechazado": "pm_card_visa_chargeDeclined",
}


@dataclass(slots=True)
class ResultadoIntento:
    resultado: ResultadoPago
    referencia_pasarela: str | None
    mensaje: str | None = None


def is_configured() -> bool:
    return bool(settings.stripe_secret_key)


def _to_cents(monto: Decimal) -> int:
    return int((monto * 100).to_integral_value())


def _cobro_sincrono(amount_cents: int, payment_method: str) -> ResultadoIntento:
    """Crea y confirma un PaymentIntent en una sola llamada (sin webhook)."""
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            payment_method=payment_method,
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        )
    except stripe.CardError as exc:  # rechazo del banco
        pi = getattr(exc.error, "payment_intent", None) if exc.error else None
        return ResultadoIntento("rechazado", getattr(pi, "id", None), exc.user_message or str(exc))
    except stripe.StripeError as exc:  # fallo de la pasarela / API
        return ResultadoIntento("error_tecnico", None, str(exc))

    if intent.status == "succeeded":
        return ResultadoIntento("aprobado", intent.id)
    if intent.status in ("requires_payment_method", "canceled"):
        return ResultadoIntento("rechazado", intent.id, f"status={intent.status}")
    return ResultadoIntento("error_tecnico", intent.id, f"status inesperado={intent.status}")


def _stub(escenario: Escenario) -> ResultadoIntento:
    ref = f"stub_{uuid.uuid4().hex[:16]}"
    if escenario == "aprobado":
        return ResultadoIntento("aprobado", ref, "stub: sin STRIPE_SECRET_KEY")
    if escenario == "rechazado":
        return ResultadoIntento("rechazado", ref, "stub: rechazo simulado")
    return ResultadoIntento("error_tecnico", None, "stub: pasarela no disponible")


async def crear_intento_pago(
    monto: Decimal, *, escenario: Escenario = "aprobado"
) -> ResultadoIntento:
    if escenario == "error_tecnico":
        # No se contacta la pasarela — distinto de un rechazo del banco (FR-030).
        return ResultadoIntento("error_tecnico", None, "No se pudo contactar la pasarela de pago")

    if not is_configured():
        return _stub(escenario)

    payment_method = _PM_POR_ESCENARIO[escenario]
    return await asyncio.to_thread(_cobro_sincrono, _to_cents(monto), payment_method)
