"""Configuración central. Todo secreto entra por entorno / `.env` (Principio X)."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Base de datos ---
    database_url: str = Field(
        default="postgresql+asyncpg://sira:sira@localhost:5432/sira", alias="DATABASE_URL"
    )
    db_echo: bool = Field(default=False, alias="DB_ECHO")

    # --- Auth / RBAC (el emisor real del JWT es la feature 008; 001 solo lo consume) ---
    jwt_secret: str = Field(default="dev-insecure-secret-change-me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, alias="JWT_EXPIRATION_MINUTES")

    # --- MinIO ---
    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")
    minio_bucket_producto_imagenes: str = Field(
        default="producto-imagenes", alias="MINIO_BUCKET_PRODUCTO_IMAGENES"
    )
    minio_bucket_comprobantes: str = Field(
        default="comprobantes-venta", alias="MINIO_BUCKET_COMPROBANTES"
    )
    minio_bucket_landing_zone: str = Field(
        default="landing-zone", alias="MINIO_BUCKET_LANDING_ZONE"
    )

    # --- ClickHouse (warehouse, feature 010). Vacío = pipeline ELT no configurado:
    #     el endpoint dev de forzar corrida usa un cargador no-op (tests con mocks). ---
    clickhouse_url: str = Field(default="", alias="CLICKHOUSE_URL")

    # --- Integraciones externas (modo test / sandbox) ---
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    sendgrid_api_key: str = Field(default="", alias="SENDGRID_API_KEY")
    sendgrid_from_email: str = Field(default="", alias="SENDGRID_FROM_EMAIL")
    openfoodfacts_base_url: str = Field(
        default="https://world.openfoodfacts.org", alias="OPENFOODFACTS_BASE_URL"
    )
    open_prices_base_url: str = Field(
        default="https://prices.openfoodfacts.org", alias="OPEN_PRICES_BASE_URL"
    )

    # --- App ---
    cors_origins: list[str] = Field(default=["http://localhost:5173"], alias="CORS_ORIGINS")
    app_env: str = Field(default="development", alias="APP_ENV")

    @field_validator("database_url", mode="after")
    @classmethod
    def _force_async_driver(cls, v: str) -> str:
        """Acepta `postgresql://` y lo normaliza al driver async que usa el backend."""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


def _ensure_jwt_secret() -> None:
    """Feature 008 (T005): `JWT_SECRET` es un secreto propio del proyecto (como las
    credenciales de MinIO), no de un tercero — se genera solo en `backend/.env` si
    aún no existe, nunca se le pide al desarrollador que lo invente a mano."""
    import secrets
    from pathlib import Path

    if "JWT_SECRET" in __import__("os").environ:
        return
    env_path = Path(__file__).resolve().parents[2] / ".env"
    try:
        contenido = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
        if "JWT_SECRET=" in contenido:
            return
        linea = f"JWT_SECRET={secrets.token_urlsafe(48)}\n"
        with env_path.open("a", encoding="utf-8") as fh:
            fh.write(("\n" if contenido and not contenido.endswith("\n") else "") + linea)
    except OSError:
        pass  # entorno de solo lectura (CI/tests): se usa el default


_ensure_jwt_secret()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
