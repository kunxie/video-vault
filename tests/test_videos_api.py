from __future__ import annotations

import hashlib

from tests.conftest import make_mp4_bytes


def _upload(client, data: bytes, *, filename: str = "clip.mp4", content_type: str = "video/mp4"):
    return client.post("/api/videos", files={"file": (filename, data, content_type)})


# --- upload -----------------------------------------------------------------


def test_upload_valid_mp4_returns_201_and_stores_object(build_client):
    client = build_client()
    data = make_mp4_bytes(2048)

    resp = _upload(client, data, filename="birthday.mp4")

    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "birthday.mp4"
    assert body["size_bytes"] == len(data)
    assert body["content_type"] == "video/mp4"
    assert body["checksum_sha256"] == hashlib.sha256(data).hexdigest()

    key = f"videos/{body['id']}.mp4"
    stored = build_client.s3.get_object(Bucket=build_client.bucket, Key=key)
    assert stored["Body"].read() == data


def test_upload_rejects_non_mp4_content_type_with_415(client):
    resp = _upload(client, b"hello world", filename="notes.txt", content_type="text/plain")
    assert resp.status_code == 415
    assert client.get("/api/videos").json() == []


def test_upload_rejects_bad_magic_bytes_with_415(client):
    # Correct extension/type, but the bytes are not an MP4 (no ftyp box).
    resp = _upload(client, b"this is definitely not a real mp4 file")
    assert resp.status_code == 415
    assert client.get("/api/videos").json() == []


def test_upload_exceeding_cap_returns_413_and_leaves_no_object(build_client):
    client = build_client(max_upload_size_bytes=16)
    resp = _upload(client, make_mp4_bytes(4096))

    assert resp.status_code == 413
    assert client.get("/api/videos").json() == []
    listing = build_client.s3.list_objects_v2(Bucket=build_client.bucket)
    assert listing.get("KeyCount", 0) == 0
    uploads = build_client.s3.list_multipart_uploads(Bucket=build_client.bucket)
    assert "Uploads" not in uploads  # aborted, nothing dangling


def test_upload_sets_hx_trigger_for_htmx_requests(client):
    resp = _upload(client, make_mp4_bytes())
    assert resp.status_code == 201
    assert "HX-Trigger" not in resp.headers

    resp = client.post(
        "/api/videos",
        files={"file": ("x.mp4", make_mp4_bytes(), "video/mp4")},
        headers={"HX-Request": "true"},
    )
    assert resp.headers.get("HX-Trigger") == "videoChanged"


# --- list / get -------------------------------------------------------------


def test_list_empty_returns_empty_array(client):
    resp = client.get("/api/videos")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_orders_newest_first(client):
    _upload(client, make_mp4_bytes(), filename="first.mp4")
    _upload(client, make_mp4_bytes(), filename="second.mp4")
    _upload(client, make_mp4_bytes(), filename="third.mp4")

    names = [v["filename"] for v in client.get("/api/videos").json()]
    assert names == ["third.mp4", "second.mp4", "first.mp4"]


def test_get_one_returns_metadata(client):
    created = _upload(client, make_mp4_bytes()).json()
    resp = client.get(f"/api/videos/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_missing_returns_404(client):
    resp = client.get("/api/videos/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# --- download ---------------------------------------------------------------


def test_download_streams_exact_bytes_as_attachment(client):
    data = make_mp4_bytes(4096)
    created = _upload(client, data, filename="trip.mp4").json()

    resp = client.get(f"/api/videos/{created['id']}/download")
    assert resp.status_code == 200
    assert resp.content == data
    assert 'attachment; filename="trip.mp4"' in resp.headers["content-disposition"]


def test_download_missing_returns_404(client):
    resp = client.get("/api/videos/00000000-0000-0000-0000-000000000000/download")
    assert resp.status_code == 404


# --- stream / watch ---------------------------------------------------------


def test_stream_without_range_returns_full_200(client):
    data = make_mp4_bytes(4096)
    created = _upload(client, data).json()

    resp = client.get(f"/api/videos/{created['id']}/stream")
    assert resp.status_code == 200
    assert resp.headers.get("accept-ranges") == "bytes"
    assert resp.content == data


def test_stream_with_range_returns_206_partial(client):
    data = make_mp4_bytes(4096)
    created = _upload(client, data).json()

    resp = client.get(f"/api/videos/{created['id']}/stream", headers={"Range": "bytes=0-9"})
    assert resp.status_code == 206
    assert resp.headers["content-range"].startswith("bytes 0-9/")
    assert resp.content == data[0:10]


def test_stream_missing_returns_404(client):
    resp = client.get("/api/videos/00000000-0000-0000-0000-000000000000/stream")
    assert resp.status_code == 404


# --- delete -----------------------------------------------------------------


def test_delete_removes_row_and_object(build_client):
    client = build_client()
    data = make_mp4_bytes()
    created = _upload(client, data).json()
    key = f"videos/{created['id']}.mp4"

    resp = client.delete(f"/api/videos/{created['id']}")
    assert resp.status_code == 204

    assert client.get(f"/api/videos/{created['id']}").status_code == 404
    assert client.get(f"/api/videos/{created['id']}/download").status_code == 404
    listing = build_client.s3.list_objects_v2(Bucket=build_client.bucket)
    keys = [obj["Key"] for obj in listing.get("Contents", [])]
    assert key not in keys


def test_delete_missing_returns_404(client):
    resp = client.delete("/api/videos/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
