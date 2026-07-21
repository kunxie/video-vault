from __future__ import annotations

import os
from collections.abc import Iterator

# moto intercepts calls to the real AWS S3 endpoint, not an arbitrary MinIO host,
# so tests point the storage client there. Provide the region/creds boto3 needs.
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

_S3_ENDPOINT = "https://s3.amazonaws.com"

import boto3
import pytest
from botocore.client import Config as BotoConfig
from fastapi.testclient import TestClient
from moto import mock_aws
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.db import get_db
from app.main import app
from app.models import Base
from app.storage import VideoStorage, get_storage

TEST_BUCKET = "video-vault-test"
DEFAULT_MAX_UPLOAD = 21_474_836_480


def _make_settings(max_upload_size_bytes: int = DEFAULT_MAX_UPLOAD) -> Settings:
    return Settings(
        database_url="sqlite://",
        minio_endpoint="http://localhost:9000",
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket=TEST_BUCKET,
        max_upload_size_bytes=max_upload_size_bytes,
        # Small parts keep multi-part paths exercised without huge test payloads.
        upload_part_size_bytes=5 * 1024 * 1024,
    )


@pytest.fixture
def build_client() -> Iterator:
    """Factory yielding a configured TestClient; lets tests tune settings per case."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)

    def _db_override() -> Iterator[Session]:
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    with mock_aws():
        s3 = boto3.client(
            "s3",
            endpoint_url=_S3_ENDPOINT,
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
            config=BotoConfig(signature_version="s3v4"),
        )
        s3.create_bucket(Bucket=TEST_BUCKET)

        def _make(max_upload_size_bytes: int = DEFAULT_MAX_UPLOAD) -> TestClient:
            settings = _make_settings(max_upload_size_bytes)
            storage = VideoStorage(
                endpoint=_S3_ENDPOINT,
                access_key="testing",
                secret_key="testing",
                bucket=TEST_BUCKET,
            )
            app.dependency_overrides[get_db] = _db_override
            app.dependency_overrides[get_storage] = lambda: storage
            app.dependency_overrides[get_settings] = lambda: settings
            return TestClient(app)

        # Expose the moto-backed S3 client so tests can assert on stored objects.
        _make.s3 = s3  # type: ignore[attr-defined]
        _make.bucket = TEST_BUCKET  # type: ignore[attr-defined]

        try:
            yield _make
        finally:
            app.dependency_overrides.clear()


@pytest.fixture
def client(build_client) -> TestClient:  # type: ignore[no-untyped-def]
    return build_client()


def make_mp4_bytes(size: int = 64) -> bytes:
    """A minimal byte blob that passes the ftyp magic check, padded to `size`."""
    header = b"\x00\x00\x00\x18ftypmp42"
    if size <= len(header):
        return header[:size]
    return header + b"\x00" * (size - len(header))
