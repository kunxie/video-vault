# Video Vault v1 — Implementation Plan

Companion to [`requirements.md`](requirements.md). Covers data model, API,
pages, storage strategy, and project layout needed to start building.

## Project Structure

```text
video-vault/
  app/
    main.py            # FastAPI app, router registration
    config.py           # Settings from env vars (pydantic-settings)
    db.py                # SQLAlchemy engine/session
    models.py           # SQLAlchemy ORM model(s)
    schemas.py           # Pydantic request/response models
    storage.py           # MinIO/boto3 wrapper (upload, stream, delete)
    routers/
      videos.py          # JSON API: /api/videos...
      pages.py            # HTML pages: /, /videos/{id}/watch
    templates/
      base.html
      index.html
      watch.html
  migrations/            # Alembic
  tests/
  Dockerfile
  pyproject.toml
```

## Data Model

Single table — v1 is single-user, so no `users` table.

### `videos`

| Column            | Type          | Notes                           |
| ----------------- | ------------- | ------------------------------- |
| `id`              | `UUID`        | PK, `gen_random_uuid()`         |
| `filename`        | `TEXT`        | Original filename, display only |
| `storage_key`     | `TEXT`        | MinIO object key, unique        |
| `size_bytes`      | `BIGINT`      | > 0                             |
| `content_type`    | `TEXT`        | Expected `video/mp4`            |
| `checksum_sha256` | `CHAR(64)`    | Computed during upload          |
| `created_at`      | `TIMESTAMPTZ` | Default `now()`                 |

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE videos (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename         TEXT NOT NULL,
    storage_key      TEXT NOT NULL UNIQUE,
    size_bytes       BIGINT NOT NULL CHECK (size_bytes > 0),
    content_type     TEXT NOT NULL,
    checksum_sha256  CHAR(64) NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_videos_created_at ON videos (created_at DESC);
```

Content-type/format validation (must be MP4) happens at the app layer, not
via a DB `CHECK` — keeps validation logic in one place.

### Migrations

Alembic. `macmini-lab`'s application-registry already expects a Postgres
migration image with an Alembic head, so this isn't an extra choice — it's
what the platform is built around.

## Storage Strategy

- Bucket: `video-vault`. Object key: `videos/{id}.mp4` — derived from the
  DB-generated UUID, not the user's filename, so there's no
  collision/encoding handling to write. The original filename lives only
  in Postgres.
- **App proxies reads and writes** rather than issuing presigned MinIO URLs.
  `macmini-lab`'s Tailscale ingress currently exposes the MinIO _console_,
  not its S3 API, to the Tailnet — so the browser can't reach MinIO
  directly. Revisit presigned URLs later if proxying becomes a throughput
  bottleneck; not a concern at v1 scale.
- **Upload**: stream the request body straight into MinIO via
  `boto3`'s `upload_fileobj` — no temp file, no full in-memory buffer.
  Enforce the 20GB cap two ways: reject upfront if `Content-Length` exceeds
  it, and abort mid-stream if actual bytes read exceed it (covers
  chunked-encoded requests with no reliable `Content-Length`). Compute the
  SHA-256 checksum incrementally in the same pass, so the file is only read
  once.
- **Download/Watch**: stream the MinIO object back through the app.
  `Watch` additionally proxies the `Range` header to MinIO's `GetObject`
  and returns `206 Partial Content` with matching `Content-Range` /
  `Accept-Ranges` headers so the browser's `<video>` element can seek.

## API Design

JSON API under `/api`, consumed by both the server-rendered pages (via
`htmx`) and, later, any SPA frontend.

| Method   | Path                        | Description                            | Response                 |
| -------- | --------------------------- | -------------------------------------- | ------------------------ |
| `POST`   | `/api/videos`               | Upload a video (`multipart/form-data`) | `201` + video JSON       |
| `GET`    | `/api/videos`               | List all videos                        | `200` + array            |
| `GET`    | `/api/videos/{id}`          | Get one video's metadata               | `200` + video JSON       |
| `GET`    | `/api/videos/{id}/download` | Download original file (attachment)    | `200`, file stream       |
| `GET`    | `/api/videos/{id}/stream`   | Watch (inline, range-request support)  | `200`/`206`, file stream |
| `DELETE` | `/api/videos/{id}`          | Delete video (object + row)            | `204`                    |

Video JSON shape:

```json
{
  "id": "uuid",
  "filename": "birthday.mp4",
  "size_bytes": 123456789,
  "content_type": "video/mp4",
  "checksum_sha256": "…",
  "created_at": "2026-07-20T12:00:00Z"
}
```

### Errors

FastAPI default `HTTPException` JSON (`{"detail": "..."}`) is enough for
v1 — no need for a structured error-code scheme with one consumer.

| Status | Cause                          |
| ------ | ------------------------------ |
| `404`  | Video id not found             |
| `413`  | Upload exceeds 20GB cap        |
| `415`  | Content type isn't `video/mp4` |

## Page Design (server-rendered)

### `GET /` — Library

```text
+-----------------------------------------------------+
| Video Vault                                          |
+-----------------------------------------------------+
| [ Choose File... ]  [ Upload ]                        |
+-----------------------------------------------------+
| birthday.mp4     512 MB   2026-07-18   Watch Download Delete |
| trip.mp4         1.2 GB   2026-07-10   Watch Download Delete |
+-----------------------------------------------------+
```

- Upload form posts to `POST /api/videos` via `htmx` (`hx-post`,
  `hx-target` on the list) so the table updates without a full reload.
- Each row's `Delete` uses `hx-delete` + `hx-confirm` ("Delete this
  video?") against `DELETE /api/videos/{id}`, removing the row on success.
- `Download` links directly to `/api/videos/{id}/download`.
- `Watch` links to the watch page (below).

### `GET /videos/{id}/watch` — Watch

```text
+-----------------------------------------------------+
| < Back                              birthday.mp4     |
+-----------------------------------------------------+
|                                                        |
|              [ <video> player, controls ]              |
|                                                        |
+-----------------------------------------------------+
```

- `<video controls src="/api/videos/{id}/stream">` — no custom player JS
  needed; range-request support on the endpoint is what makes native
  browser seeking work.

## Configuration

Env vars (via `pydantic-settings`):

| Variable                | Purpose                      |
| ----------------------- | ---------------------------- |
| `DATABASE_URL`          | Postgres connection string   |
| `MINIO_ENDPOINT`        | MinIO S3 API endpoint        |
| `MINIO_ACCESS_KEY`      | MinIO credential             |
| `MINIO_SECRET_KEY`      | MinIO credential             |
| `MINIO_BUCKET`          | Bucket name (`video-vault`)  |
| `MAX_UPLOAD_SIZE_BYTES` | Default `21474836480` (20GB) |

## Acceptance Criteria

### Upload

- A valid MP4 ≤ 20GB uploaded via `POST /api/videos` returns `201` with the
  video JSON; a matching object exists in MinIO at `videos/{id}.mp4` and a
  matching row exists in Postgres.
- A file whose `Content-Length` exceeds 20GB is rejected with `413` before
  the body is read — no object is written to MinIO.
- A chunked-encoded upload with no reliable `Content-Length` that exceeds
  20GB in actual bytes is aborted mid-stream with `413`, and any partial
  MinIO object is cleaned up (no orphaned object left behind).
- A file that isn't a valid `.mp4` (wrong extension, or fails the format
  check) is rejected with `415` — no object or row is created.
- The stored `checksum_sha256` equals an independently computed SHA-256 of
  the uploaded bytes (verify by re-downloading and hashing).
- After a successful upload, the video appears in `GET /api/videos` and in
  the library page's table without a full page reload.

### List

- With zero videos, `GET /api/videos` returns `200` with an empty array;
  the library page renders with no rows and the upload form still present.
- With N videos, `GET /api/videos` returns all N, ordered by `created_at`
  descending (newest first).

### Download

- `GET /api/videos/{id}/download` on an existing id returns `200`, streams
  the exact original bytes (its SHA-256 matches `checksum_sha256`), and
  sets `Content-Disposition: attachment` with the original filename.
- A non-existent id returns `404`.

### Watch / Streaming

- `GET /api/videos/{id}/stream` without a `Range` header returns `200` with
  the full file and an `Accept-Ranges: bytes` header.
- The same endpoint with a `Range` header (e.g. `bytes=0-1023`) returns
  `206 Partial Content`, a correct `Content-Range` header, and only the
  requested byte range in the body.
- The watch page (`/videos/{id}/watch`) renders a `<video>` element whose
  `src` points at the stream endpoint; seeking in the browser triggers
  ranged (`206`) requests rather than re-downloading the whole file
  (verify via the browser network tab).
- A non-existent id returns `404` from both the stream endpoint and the
  watch page.

### Delete

- `DELETE /api/videos/{id}` on an existing id returns `204` and removes
  both the Postgres row and the MinIO object — a subsequent `GET`,
  `download`, or `stream` on the same id returns `404`.
- A non-existent id returns `404`.
- Using the library page's delete action (with confirmation) removes the
  row from the table without a full page reload.

### Cross-cutting

- Uploading a large file (tens of GB) does not scale the app process's
  memory with file size — confirm via RSS monitoring during a large test
  upload that the file is streamed, not buffered.
- The app is reachable only over Tailscale in the deployed environment; no
  public ingress exists for it.
- Alembic migrations apply cleanly to a fresh Postgres database and produce
  the `videos` table exactly as specified above.
- `404`/`413`/`415` error responses use FastAPI's default
  `{"detail": "..."}` JSON shape.

## Testing

- Route/unit tests with a mocked storage layer (`moto` for the S3/MinIO
  calls) and a real local Postgres — enough to test behavior without
  standing up the full platform.
- Testcontainers-backed integration tests are an explicit v2+ idea (see
  `README.md`), not v1 — keeps the test setup as simple as the app.
