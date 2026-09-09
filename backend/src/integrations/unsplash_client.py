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
import re
from typing import Any

import httpx

from src.core.config import settings

log = logging.getLogger("sira.unsplash")
_TIMEOUT = httpx.Timeout(6.0)

# Estado en memoria de la cuota Unsplash (50 req/hora en tier Demo)
_rate_limit_info: dict[str, Any] = {
    "limit": 50,
    "remaining": None,
    "reset": None,
}


def is_configured() -> bool:
    return bool(settings.unsplash_access_key)


def obtener_estado_cuota() -> dict[str, Any]:
    """Devuelve la información más reciente sobre la cuota de Unsplash."""
    return dict(_rate_limit_info)


def _actualizar_headers_cuota(headers: httpx.Headers) -> None:
    rem = headers.get("X-Ratelimit-Remaining")
    lim = headers.get("X-Ratelimit-Limit")
    res = headers.get("X-Ratelimit-Reset")
    if rem is not None:
        try:
            _rate_limit_info["remaining"] = int(rem)
        except ValueError:
            pass
    if lim is not None:
        try:
            _rate_limit_info["limit"] = int(lim)
        except ValueError:
            pass
    if res is not None:
        try:
            _rate_limit_info["reset"] = int(res)
        except ValueError:
            pass


def limpiar_terminos_producto(
    nombre: str | None,
    categoria: str | None = None,
    tipo: str | None = None,
) -> list[str]:
    """Genera una lista priorizada de términos de búsqueda limpios para Unsplash.

    1. Nombre limpio sin pesos (' · 14 OZ') ni signos conflictivos (:, /, -).
    2. Categoría normalizada (ej: 'BREAD', 'SEAFOOD FROZEN').
    3. Tipo de producto normalizado.
    """
    candidatos: list[str] = []

    def _limpiar(texto: str) -> str:
        t = texto.split(" · ")[0]
        t = re.sub(r"[:\-_/]", " ", t)
        t = re.sub(r"\b\d+(\.\d+)?\s*(oz|lb|kg|g|ml|l|pk|ct|count)\b", "", t, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", t).strip()

    if nombre:
        n_limpio = _limpiar(nombre)
        if len(n_limpio) >= 3 and n_limpio.lower() not in [c.lower() for c in candidatos]:
            candidatos.append(n_limpio)

    if categoria:
        cat_limpio = _limpiar(categoria)
        if len(cat_limpio) >= 3 and cat_limpio.lower() not in [c.lower() for c in candidatos]:
            candidatos.append(cat_limpio)

    if tipo:
        tipo_limpio = _limpiar(tipo)
        if len(tipo_limpio) >= 3 and tipo_limpio.lower() not in [c.lower() for c in candidatos]:
            candidatos.append(tipo_limpio)

    return candidatos


async def buscar_imagen(consulta: str) -> str | None:
    """Devuelve la URL (`urls.small`, ~400px) de la primera foto que matchee
    `consulta`, o `None`. Nunca lanza."""
    if not is_configured() or not consulta or not consulta.strip():
        return None

    if _rate_limit_info["remaining"] is not None and _rate_limit_info["remaining"] <= 0:
        log.warning("unsplash: cuota agotada (0 restantes), llamada omitida para %r", consulta)
        return None

    url = f"{settings.unsplash_base_url}/search/photos"
    params = {"query": consulta.strip(), "per_page": 1, "orientation": "squarish"}
    headers = {"Authorization": f"Client-ID {settings.unsplash_access_key}"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
        _actualizar_headers_cuota(resp.headers)
        if resp.status_code in (403, 429):
            _rate_limit_info["remaining"] = 0
            log.warning("unsplash: límite de rate alcanzado (%s)", resp.status_code)
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


async def buscar_imagen_producto(
    nombre: str | None,
    categoria: str | None = None,
    tipo: str | None = None,
) -> str | None:
    """Busca una foto intentando primero con el nombre limpio y cayendo a
    categoría o tipo de producto si el primero no arroja resultados."""
    terminos = limpiar_terminos_producto(nombre, categoria, tipo)
    for termino in terminos:
        url = await buscar_imagen(termino)
        if url:
            return url
        # Si la cuota se agotó durante la llamada, no intentar fallbacks
        if _rate_limit_info["remaining"] is not None and _rate_limit_info["remaining"] <= 0:
            break
    return None

