from __future__ import annotations

from fastapi import FastAPI

from app.routers import pages, videos

app = FastAPI(title="Video Vault", version="0.1.0")

app.include_router(videos.router)
app.include_router(pages.router)


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}
