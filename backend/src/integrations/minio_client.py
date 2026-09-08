"""Cliente MinIO — imágenes de producto subidas por el usuario (FR-013).

Bucket `producto-imagenes` con política public-read: el navegador resuelve la
imagen directo por URL. Si MinIO no está disponible, se lanza `RuntimeError` y el
llamador reporta el error (subir una imagen sí es una acción que puede fallar
ruidosamente — a diferencia del autocompletado, que se degrada en silencio).
"""

from __future__ import annotations

import io
import json
import logging
import uuid
from functools import lru_cache

from minio import Minio
from minio.error import S3Error

from src.core.config import settings

log = logging.getLogger("sira.minio")

_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_MAX_BYTES = 5 * 1024 * 1024

_POLICY_PUBLIC_READ = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": ["arn:aws:s3:::{bucket}/*"],
        }
    ],
}


@lru_cache(maxsize=1)
def _cliente() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _asegurar_bucket(bucket: str) -> None:
    cli = _cliente()
    if not cli.bucket_exists(bucket):
        cli.make_bucket(bucket)
    politica = json.loads(json.dumps(_POLICY_PUBLIC_READ).replace("{bucket}", bucket))
    try:
        cli.set_bucket_policy(bucket, json.dumps(politica))
    except S3Error:  # pragma: no cover - política ya aplicada / permisos
        pass


def subir_imagen_producto(product_id: int, data: bytes, content_type: str) -> str:
    """Sube la imagen y devuelve la URL pública. Valida tipo y tamaño."""
    if content_type not in _EXT:
        raise RuntimeError("Formato no soportado (usá JPG, PNG o WEBP)")
    if len(data) > _MAX_BYTES:
        raise RuntimeError("La imagen supera los 5 MB")

    bucket = settings.minio_bucket_producto_imagenes
    key = f"productos/{product_id}/{uuid.uuid4().hex}.{_EXT[content_type]}"
    try:
        _asegurar_bucket(bucket)
        _cliente().put_object(
            bucket, key, io.BytesIO(data), length=len(data), content_type=content_type
        )
    except (S3Error, OSError) as exc:  # noqa: BLE001
        log.exception("minio: falló la subida de imagen de producto %s", product_id)
        raise RuntimeError("No se pudo guardar la imagen (almacenamiento no disponible)") from exc

    return f"{settings.minio_public_url.rstrip('/')}/{bucket}/{key}"
