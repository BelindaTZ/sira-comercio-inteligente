"""Cliente Open Food Facts — autocompletado de producto nuevo (FR-013).

API pública de solo lectura, sin API key (research.md #10). Si no hay coincidencia
o el servicio no responde, se devuelve None y el formulario queda editable manual.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from src.core.config import settings

_TIMEOUT = httpx.Timeout(5.0)


@dataclass(slots=True)
class ProductoExterno:
    nombre: str | None
    marca: str | None
    categoria: str | None
    imagen_url: str | None


async def buscar_por_barcode(barcode: str) -> ProductoExterno | None:
    url = f"{settings.openfoodfacts_base_url}/api/v2/product/{barcode}.json"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("status") != 1:
            return None
        p = data.get("product", {})
        return ProductoExterno(
            nombre=p.get("product_name") or None,
            marca=p.get("brands") or None,
            categoria=(p.get("categories") or "").split(",")[0].strip() or None,
            imagen_url=p.get("image_url") or None,
        )
    except (httpx.HTTPError, ValueError):
        return None
