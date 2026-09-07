"""Cliente Open Prices (prices.openfoodfacts.org) — precio de referencia de
competencia para productos en vivo con código de barras real (research.md §5).

Proyecto de la misma organización que Open Food Facts (ya aprobado en el Stack).
Lectura pública, sin API key. `best-effort`: cualquier fallo, timeout o ausencia
de dato devuelve `None` y no bloquea nada (FR-014, Principio X no exige
disponibilidad de terceros para el cálculo operativo propio).
"""

from __future__ import annotations

import logging

import httpx

from src.core.config import settings

logger = logging.getLogger("sira.integrations.open_prices")

_TIMEOUT = httpx.Timeout(5.0)


async def ultimo_precio_por_barcode(barcode: str) -> float | None:
    """Precio más reciente reportado en Open Prices para ese código de barras, o
    `None` si no hay dato / el servicio no responde."""
    if not barcode:
        return None
    url = f"{settings.open_prices_base_url}/api/v1/prices"
    params = {"product_code": barcode, "order_by": "-date", "size": 1}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return None
        items = resp.json().get("items") or []
        if not items:
            return None
        precio = items[0].get("price")
        return float(precio) if precio is not None else None
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        logger.info("Open Prices sin respuesta útil para %s", barcode)
        return None
