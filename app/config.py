from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables (or a local .env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "video-vault"

    # 20 GiB. Enforced by the app on upload; MinIO itself allows much larger.
    max_upload_size_bytes: int = 21_474_836_480
    # S3 multipart part size. Must be >= 5 MiB for all-but-last part.
    upload_part_size_bytes: int = 8 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    # Values come from the environment; mypy can't see that, hence the ignore.
    return Settings()  # type: ignore[call-arg]
