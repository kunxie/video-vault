from __future__ import annotations

from tests.conftest import make_mp4_bytes


def test_index_renders_with_no_videos(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Video Vault" in resp.text
    assert "No videos yet" in resp.text


def test_index_lists_uploaded_video(client):
    client.post("/api/videos", files={"file": ("holiday.mp4", make_mp4_bytes(), "video/mp4")})
    resp = client.get("/")
    assert resp.status_code == 200
    assert "holiday.mp4" in resp.text


def test_fragment_returns_rows(client):
    client.post("/api/videos", files={"file": ("holiday.mp4", make_mp4_bytes(), "video/mp4")})
    resp = client.get("/fragments/videos")
    assert resp.status_code == 200
    assert "holiday.mp4" in resp.text
    assert "Watch" in resp.text


def test_watch_page_renders_player(client):
    created = client.post(
        "/api/videos", files={"file": ("holiday.mp4", make_mp4_bytes(), "video/mp4")}
    ).json()
    resp = client.get(f"/videos/{created['id']}/watch")
    assert resp.status_code == 200
    assert f"/api/videos/{created['id']}/stream" in resp.text
    assert "<video" in resp.text


def test_watch_page_missing_returns_404(client):
    resp = client.get("/videos/00000000-0000-0000-0000-000000000000/watch")
    assert resp.status_code == 404
