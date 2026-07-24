from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, make_url


class DatabaseSettings(BaseSettings):
    """Database-only configuration used by the finite migration command."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Local development may use DATABASE_URL. Production supplies the five
    # discrete values below so credentials never need to be composed in a
    # Kubernetes Secret or shell command.
    database_url: str | None = None
    database_username: str | None = None
    database_password: str | None = None
    database_host: str | None = None
    database_port: int | None = None
    database_name: str | None = None

    @model_validator(mode="after")
    def validate_database_configuration(self) -> DatabaseSettings:
        if self.database_url:
            return self

        discrete_values = {
            "database_username": self.database_username,
            "database_password": self.database_password,
            "database_host": self.database_host,
            "database_port": self.database_port,
            "database_name": self.database_name,
        }
        missing = [name for name, value in discrete_values.items() if value in (None, "")]
        if missing:
            message = "database_url or all discrete database settings are required"
            raise ValueError(message)
        return self

    def sqlalchemy_database_url(self) -> URL:
        """Return a SQLAlchemy URL without manually interpolating credentials."""
        if self.database_url:
            return make_url(self.database_url)
        return URL.create(
            "postgresql+psycopg",
            username=self.database_username,
            password=self.database_password,
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        )


class Settings(DatabaseSettings):
    """Application configuration, sourced from environment variables (or a local .env)."""

    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "video-vault"

    # 20 GiB. Enforced by the app on upload; MinIO itself allows much larger.
    max_upload_size_bytes: int = 21_474_836_480
    # S3 multipart part size. Must be >= 5 MiB for all-but-last part.
    upload_part_size_bytes: int = 8 * 1024 * 1024


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


@lru_cache
def get_settings() -> Settings:
    # Values come from the environment; mypy can't see that, hence the ignore.
    return Settings()  # type: ignore[call-arg]
