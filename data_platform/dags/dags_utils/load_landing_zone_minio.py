"""Load raw — vuelca el resultado del Extract, tal cual, al bucket MinIO
`landing-zone` antes de tocar el warehouse (feature 010, Principio III).

El objeto crudo queda como evidencia reproducible de qué trajo cada corrida:
`landing-zone/<entidad>/<corrida_id>/<fecha_inicio>.json`.

`cliente_minio` es cualquier objeto con `put_object(bucket, key, data, length,
content_type=...)` (la firma del SDK `minio`). Un doble de test en memoria basta.
"""

from __future__ import annotations

import io
import json
from datetime import date, datetime
from decimal import Decimal


def _serializable(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime | date):
        return v.isoformat()
    return v


def _dump(rows: list[dict]) -> bytes:
    limpio = [{k: _serializable(v) for k, v in r.items()} for r in rows]
    return json.dumps(limpio, ensure_ascii=False).encode("utf-8")


def volcar(
    cliente_minio,
    *,
    bucket: str,
    nombre_entidad: str,
    corrida_id: int,
    fecha_inicio: datetime,
    rows: list[dict],
) -> str:
    """Sube el raw y devuelve la key del objeto creado."""
    key = f"{nombre_entidad}/{corrida_id}/{fecha_inicio.strftime('%Y%m%dT%H%M%S')}.json"
    payload = _dump(rows)
    cliente_minio.put_object(
        bucket,
        key,
        io.BytesIO(payload),
        length=len(payload),
        content_type="application/json",
    )
    return key
