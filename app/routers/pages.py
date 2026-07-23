from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Video

router = APIRouter(include_in_schema=False)

DbSession = Annotated[Session, Depends(get_db)]

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


templates.env.filters["human_size"] = _human_size


def _list_videos(db: Session) -> list[Video]:
    stmt = select(Video).order_by(Video.created_at.desc())
    return list(db.execute(stmt).scalars().all())


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: DbSession) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"videos": _list_videos(db)})


@router.get("/fragments/videos", response_class=HTMLResponse)
def video_rows(request: Request, db: DbSession) -> HTMLResponse:
    return templates.TemplateResponse(request, "_video_rows.html", {"videos": _list_videos(db)})


@router.get("/videos/{video_id}/watch", response_class=HTMLResponse)
def watch(request: Request, video_id: uuid.UUID, db: DbSession) -> HTMLResponse:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return templates.TemplateResponse(request, "watch.html", {"video": video})
