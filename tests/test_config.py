from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def _storage_settings() -> dict[str, str]:
    return {
        "minio_endpoint": "http://localhost:9000",
        "minio_access_key": "test",
        "minio_secret_key": "test",
    }


def test_database_url_override_remains_supported() -> None:
    settings = Settings(database_url="sqlite://", **_storage_settings())

    assert settings.sqlalchemy_database_url().drivername == "sqlite"


def test_discrete_database_settings_create_escaped_url() -> None:
    settings = Settings(
        database_username="vault@example.com",
        database_password="p@ss/word%value",
        database_host="postgres-rw.data.svc.cluster.local",
        database_port=5432,
        database_name="video-vault",
        **_storage_settings(),
    )

    url = settings.sqlalchemy_database_url()
    assert url.username == "vault@example.com"
    assert url.password == "p@ss/word%value"
    assert url.database == "video-vault"
    assert "%40" in url.render_as_string(hide_password=False)


def test_database_configuration_is_required() -> None:
    with pytest.raises(ValidationError, match="database_url or all discrete"):
        Settings(**_storage_settings())
