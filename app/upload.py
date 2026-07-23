from __future__ import annotations

import hashlib

from streaming_form_data.targets import BaseTarget

from app.storage import VideoStorage

# MP4 files carry an "ftyp" box; on a well-formed file bytes 4..8 spell "ftyp".
_MP4_MAGIC = b"ftyp"
_MAGIC_PEEK_BYTES = 12


class UploadTooLargeError(Exception):
    """Uploaded bytes exceeded the configured cap."""


class InvalidVideoError(Exception):
    """The uploaded part is not an acceptable MP4 (wrong type/extension/magic)."""


class MinioMultipartTarget(BaseTarget):  # type: ignore[misc]  # BaseTarget is untyped
    """A streaming-form-data target that pipes an uploaded file straight into MinIO.

    Bytes are never buffered in full: they are hashed, size-checked, and pushed to
    an S3 multipart upload as ~part_size chunks. On any failure the caller invokes
    :meth:`abort`, which aborts the multipart upload so no orphan object survives.
    """

    def __init__(
        self,
        storage: VideoStorage,
        key: str,
        *,
        max_size: int,
        part_size: int,
    ) -> None:
        super().__init__()
        self._storage = storage
        self._key = key
        self._max_size = max_size
        self._part_size = part_size

        self._upload_id: str | None = None
        self._buffer = bytearray()
        self._parts: list[dict[str, object]] = []
        self._part_number = 0

        self._hasher = hashlib.sha256()
        self._total = 0

        self._magic_checked = False
        self._magic_peek = bytearray()

        self.completed = False
        self.aborted = False

    # --- streaming-form-data hooks -----------------------------------------

    def on_start(self) -> None:
        # The client-declared content type is unreliable (and not yet populated at
        # this point in streaming-form-data), so gate on the extension here and on
        # the ftyp magic bytes once data arrives.
        filename = (self.multipart_filename or "").lower()
        if not filename.endswith(".mp4"):
            raise InvalidVideoError("Only MP4 files are accepted")
        self._upload_id = self._storage.create_multipart_upload(self._key, "video/mp4")

    def on_data_received(self, chunk: bytes) -> None:
        if not chunk:
            return
        if not self._magic_checked:
            self._magic_peek.extend(chunk)
            if len(self._magic_peek) >= _MAGIC_PEEK_BYTES:
                self._check_magic()

        self._total += len(chunk)
        if self._total > self._max_size:
            raise UploadTooLargeError("Upload exceeds the maximum allowed size")

        self._hasher.update(chunk)
        self._buffer.extend(chunk)
        if len(self._buffer) >= self._part_size:
            self._flush_part()

    def on_finish(self) -> None:
        if not self._magic_checked:
            # File shorter than the peek window: validate whatever we have.
            self._check_magic()
        if self._buffer:
            self._flush_part()
        if not self._parts:
            raise InvalidVideoError("Uploaded file is empty")

        assert self._upload_id is not None
        self._storage.complete_multipart_upload(self._key, self._upload_id, self._parts)
        self.completed = True

    # --- helpers ------------------------------------------------------------

    def _check_magic(self) -> None:
        self._magic_checked = True
        if self._magic_peek[4:8] != _MP4_MAGIC:
            raise InvalidVideoError("File is not a valid MP4 (missing ftyp box)")

    def _flush_part(self) -> None:
        assert self._upload_id is not None
        self._part_number += 1
        etag = self._storage.upload_part(
            self._key, self._upload_id, self._part_number, bytes(self._buffer)
        )
        self._parts.append({"PartNumber": self._part_number, "ETag": etag})
        self._buffer.clear()

    def abort(self) -> None:
        """Best-effort cleanup of a partial multipart upload."""
        if self._upload_id is not None and not self.aborted and not self.completed:
            self._storage.abort_multipart_upload(self._key, self._upload_id)
            self.aborted = True

    # --- results ------------------------------------------------------------

    @property
    def checksum(self) -> str:
        return self._hasher.hexdigest()

    @property
    def size(self) -> int:
        return self._total

    @property
    def filename(self) -> str:
        return self.multipart_filename or "video.mp4"
