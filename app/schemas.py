from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class VideoOut(BaseModel):
    """Public JSON shape for a video. Storage key is intentionally not exposed."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    size_bytes: int
    content_type: str
    checksum_sha256: str
    created_at: datetime.datetime
