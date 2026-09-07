"""T026 — integración real con Stripe Payment Intents (modo test).

Se salta si no hay `STRIPE_SECRET_KEY` configurada. Verifica que los 3 resultados
de FR-030 se obtienen con las tarjetas de prueba oficiales, no con lógica propia.
"""

from decimal import Decimal

import pytest
from src.integrations import stripe_client

pytestmark = pytest.mark.asyncio

requiere_stripe = pytest.mark.skipif(
    not stripe_client.is_configured(), reason="STRIPE_SECRET_KEY no configurada"
)


@requiere_stripe
async def test_pago_aprobado_devuelve_payment_intent_real():
    r = await stripe_client.crear_intento_pago(Decimal("10.00"), escenario="aprobado")
    assert r.resultado == "aprobado"
    assert r.referencia_pasarela and r.referencia_pasarela.startswith("pi_")


@requiere_stripe
async def test_rechazo_del_banco_es_distinto_de_error_tecnico():
    rechazo = await stripe_client.crear_intento_pago(Decimal("10.00"), escenario="rechazado")
    error = await stripe_client.crear_intento_pago(Decimal("10.00"), escenario="error_tecnico")
    assert rechazo.resultado == "rechazado"
    assert error.resultado == "error_tecnico"
    assert error.referencia_pasarela is None  # no se contactó la pasarela


async def test_error_tecnico_no_requiere_red():
    # Siempre determinístico, con o sin clave: no se llama a Stripe.
    r = await stripe_client.crear_intento_pago(Decimal("1.00"), escenario="error_tecnico")
    assert r.resultado == "error_tecnico"
