from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from streaming_form_data import StreamingFormDataParser

from app.config import Settings, get_settings
from app.db import get_db
from app.models import Video
from app.schemas import VideoOut
from app.storage import (
    InvalidRangeError,
    ObjectNotFoundError,
    ObjectStream,
    VideoStorage,
    get_storage,
)
from app.upload import InvalidVideoError, MinioMultipartTarget, UploadTooLargeError

router = APIRouter(prefix="/api/videos", tags=["videos"])

DbSession = Annotated[Session, Depends(get_db)]
Storage = Annotated[VideoStorage, Depends(get_storage)]
Config = Annotated[Settings, Depends(get_settings)]

_HX_TRIGGER = "videoChanged"
_VIDEO_NOT_FOUND = "Video not found"


def _notify_htmx(request: Request, response: Response) -> None:
    """Tell an htmx-driven page that the video list changed, so it can refresh."""
    if request.headers.get("HX-Request"):
        response.headers["HX-Trigger"] = _HX_TRIGGER


def _get_video_or_404(db: Session, video_id: uuid.UUID) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _VIDEO_NOT_FOUND)
    return video


def _stream_response(
    stream: ObjectStream, media_type: str, **extra_headers: str
) -> StreamingResponse:
    headers = {"Content-Length": str(stream.content_length), **extra_headers}
    status_code = status.HTTP_200_OK
    if stream.content_range is not None:
        headers["Content-Range"] = stream.content_range
        status_code = status.HTTP_206_PARTIAL_CONTENT
    return StreamingResponse(
        stream.iter_chunks(),
        status_code=status_code,
        media_type=media_type,
        headers=headers,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=VideoOut)
async def upload_video(
    request: Request,
    response: Response,
    db: DbSession,
    storage: Storage,
    settings: Config,
) -> Video:
    # Cheap upfront rejection: if the declared body already exceeds the cap, bail
    # before reading a single byte or opening a multipart upload.
    content_length = request.headers.get("content-length")
    if content_length is not None and int(content_length) > settings.max_upload_size_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, "Upload exceeds the maximum allowed size"
        )

    video_id = uuid.uuid4()
    key = f"videos/{video_id}.mp4"
    target = MinioMultipartTarget(
        storage,
        key,
        max_size=settings.max_upload_size_bytes,
        part_size=settings.upload_part_size_bytes,
    )
    parser = StreamingFormDataParser(
        headers={"Content-Type": request.headers.get("content-type", "")}
    )
    parser.register("file", target)

    try:
        async for chunk in request.stream():
            parser.data_received(chunk)
    except UploadTooLargeError:
        target.abort()
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, "Upload exceeds the maximum allowed size"
        ) from None
    except InvalidVideoError as exc:
        target.abort()
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from None
    except Exception:
        target.abort()
        raise

    if not target.completed:
        target.abort()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "No file field named 'file' provided"
        )

    video = Video(
        id=video_id,
        filename=target.filename,
        storage_key=key,
        size_bytes=target.size,
        content_type="video/mp4",
        checksum_sha256=target.checksum,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    _notify_htmx(request, response)
    return video


@router.get("", response_model=list[VideoOut])
async def list_videos(db: DbSession) -> list[Video]:
    stmt = select(Video).order_by(Video.created_at.desc())
    return list(db.execute(stmt).scalars().all())


@router.get("/{video_id}", response_model=VideoOut)
async def get_video(video_id: uuid.UUID, db: DbSession) -> Video:
    return _get_video_or_404(db, video_id)


@router.get("/{video_id}/download")
async def download_video(video_id: uuid.UUID, db: DbSession, storage: Storage) -> StreamingResponse:
    video = _get_video_or_404(db, video_id)
    try:
        stream = storage.get_object(video.storage_key)
    except ObjectNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _VIDEO_NOT_FOUND) from None
    # Quote-strip the filename so it can't break out of the header value.
    safe_name = video.filename.replace('"', "")
    return _stream_response(
        stream,
        video.content_type,
        **{"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.get("/{video_id}/stream")
async def stream_video(
    video_id: uuid.UUID, request: Request, db: DbSession, storage: Storage
) -> StreamingResponse:
    video = _get_video_or_404(db, video_id)
    range_header = request.headers.get("range")
    try:
        stream = storage.get_object(video.storage_key, range_header=range_header)
    except ObjectNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _VIDEO_NOT_FOUND) from None
    except InvalidRangeError:
        raise HTTPException(
            status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, "Requested range not satisfiable"
        ) from None
    return _stream_response(stream, video.content_type, **{"Accept-Ranges": "bytes"})


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: uuid.UUID, request: Request, db: DbSession, storage: Storage
) -> Response:
    video = _get_video_or_404(db, video_id)
    storage.delete_object(video.storage_key)
    db.delete(video)
    db.commit()

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _notify_htmx(request, response)
    return response
