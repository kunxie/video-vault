from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import get_settings

if TYPE_CHECKING:
    from mypy_boto3_s3.type_defs import CompletedMultipartUploadTypeDef

# How much of an object's body to read per chunk when streaming back to a client.
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024


class ObjectNotFoundError(Exception):
    """The requested object key does not exist in the bucket."""


class InvalidRangeError(Exception):
    """The client's Range header could not be satisfied for this object."""


@dataclass
class ObjectStream:
    """A readable object (or byte range) returned from storage."""

    body: Any  # botocore StreamingBody
    content_length: int
    content_range: str | None  # set only for a ranged (206) response

    def iter_chunks(self) -> Iterator[bytes]:
        yield from self.body.iter_chunks(chunk_size=_DOWNLOAD_CHUNK_SIZE)


class VideoStorage:
    """Thin wrapper over the S3/MinIO API for the operations this app needs."""

    def __init__(self, *, endpoint: str, access_key: str, secret_key: str, bucket: str) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
        )
        self._bucket = bucket

    def ensure_bucket(self) -> None:
        """Create the bucket if it does not already exist (idempotent)."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    def check_bucket(self) -> None:
        """Verify that the configured bucket is reachable without writing to it."""
        self._client.head_bucket(Bucket=self._bucket)

    # --- multipart upload ---------------------------------------------------

    def create_multipart_upload(self, key: str, content_type: str) -> str:
        response = self._client.create_multipart_upload(
            Bucket=self._bucket, Key=key, ContentType=content_type
        )
        return str(response["UploadId"])

    def upload_part(self, key: str, upload_id: str, part_number: int, body: bytes) -> str:
        response = self._client.upload_part(
            Bucket=self._bucket,
            Key=key,
            UploadId=upload_id,
            PartNumber=part_number,
            Body=body,
        )
        return str(response["ETag"])

    def complete_multipart_upload(
        self, key: str, upload_id: str, parts: list[dict[str, Any]]
    ) -> None:
        self._client.complete_multipart_upload(
            Bucket=self._bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload=cast("CompletedMultipartUploadTypeDef", {"Parts": parts}),
        )

    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        self._client.abort_multipart_upload(Bucket=self._bucket, Key=key, UploadId=upload_id)

    # --- download / delete --------------------------------------------------

    def get_object(self, key: str, *, range_header: str | None = None) -> ObjectStream:
        kwargs: dict[str, Any] = {"Bucket": self._bucket, "Key": key}
        if range_header:
            kwargs["Range"] = range_header
        try:
            response = self._client.get_object(**kwargs)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404"):
                raise ObjectNotFoundError(key) from exc
            if code in ("InvalidRange", "416"):
                raise InvalidRangeError(range_header or "") from exc
            raise
        return ObjectStream(
            body=response["Body"],
            content_length=int(response["ContentLength"]),
            content_range=response.get("ContentRange"),
        )

    def delete_object(self, key: str) -> None:
        # S3 DeleteObject is idempotent: deleting a missing key succeeds.
        self._client.delete_object(Bucket=self._bucket, Key=key)


@lru_cache
def get_storage() -> VideoStorage:
    settings = get_settings()
    return VideoStorage(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
    )
