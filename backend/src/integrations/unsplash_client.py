"""Cliente Unsplash — imagen genérica para productos del dataset (FR-013).

El dataset Dunnhumby ("The Complete Journey") llega sin nombre comercial ni foto.
Para que el Catálogo y el Inventario no se vean vacíos se busca en Unsplash una
foto genérica a partir del nombre/categoría del producto.

Sólo lectura, sólo el Access Key (`client_id`). Si no hay clave, la búsqueda no
responde, o no hay resultados → se devuelve `None` y el llamador usa el
placeholder por categoría (Principio II: la operación no depende de la imagen).

Tier "Demo" de Unsplash: 50 requests/hora — no sirve para las 92k del catálogo;
se usa bajo demanda (una foto cuando alguien la pide) o en lotes chicos.
"""

from __future__ import annotations

import logging

import httpx

from src.core.config import settings

log = logging.getLogger("sira.unsplash")
_TIMEOUT = httpx.Timeout(6.0)


def is_configured() -> bool:
    return bool(settings.unsplash_access_key)


async def buscar_imagen(consulta: str) -> str | None:
    """Devuelve la URL (`urls.small`, ~400px) de la primera foto que matchee
    `consulta`, o `None`. Nunca lanza."""
    if not is_configured() or not consulta or not consulta.strip():
        return None
    url = f"{settings.unsplash_base_url}/search/photos"
    params = {"query": consulta.strip(), "per_page": 1, "orientation": "squarish"}
    headers = {"Authorization": f"Client-ID {settings.unsplash_access_key}"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
        if resp.status_code == 403:
            log.warning("unsplash: límite de rate alcanzado (403)")
            return None
        resp.raise_for_status()
        resultados = resp.json().get("results") or []
        if not resultados:
            return None
        urls = resultados[0].get("urls") or {}
        return urls.get("small") or urls.get("regular") or urls.get("thumb")
    except (httpx.HTTPError, ValueError, KeyError) as exc:  # noqa: BLE001
        log.info("unsplash: sin imagen para %r (%s)", consulta, exc)
        return None
