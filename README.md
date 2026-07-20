# Video Vault

A personal media service for storing and watching MP4 videos: upload,
download, delete, and watch online. Runs on the `macmini-lab` platform
(single-node K3s), reusing its shared MinIO (object storage) and Postgres
(metadata). Built for personal use and as a learning project.

Current scope: [`docs/v1/requirements.md`](docs/v1/requirements.md).

## Future Ideas

Not committed to any version — a backlog of directions to grow into, kept
here so v1 can stay small on purpose. Grouped by theme, roughly ordered by
how likely each is to come next.

### Upload & Transfer

- **Resumable/chunked upload** — S3 multipart upload lifecycle, an
  upload-session table, and client-side chunking (tus protocol or hand-rolled).
  Deferred from v1 deliberately as a learning exercise.
- **Presigned MinIO URLs for direct-to-storage upload** — pairs with
  resumable/chunked upload: the app orchestrates the multipart session
  (create upload, hand out a presigned URL per part, track ETags,
  complete/abort) while the browser uploads each chunk directly to MinIO,
  instead of proxying every byte through the app twice. Needs exposing
  MinIO's S3 API over Tailscale first (today only its console is exposed) —
  v1 proxies reads/writes through the app since this isn't available yet.
- Drag-and-drop / multi-file batch upload.
- Client-side checksum + duplicate detection before upload (skip re-uploading
  a file already stored).
- Live upload progress via WebSocket/SSE instead of a plain progress bar.

### Playback & Media Processing

- Thumbnail generation (extract a frame with `ffmpeg` on upload).
- Transcoding to adaptive bitrate (HLS/DASH) for smoother playback on slow
  links, with multiple renditions.
- Background job processing for transcoding (Celery/RQ, or native K8s Jobs) —
  a chance to learn async task queues outside the request/response cycle.
- Resume playback where you left off (watch progress tracking per video).
- Subtitle/caption support.
- Support for video formats beyond MP4 (transcode on ingest).
- **Generalize videos → media**: support pictures alongside video. Not just
  a new format value — `content_type` already covers additional video
  formats for free, but pictures are a different kind of media. Needs
  renaming the `videos` table/API to `media` with a `media_type`
  (`video`/`image`) column, since the schema and endpoints are currently
  video-specific by design.

### Organization

- Search, tags, and categories.
- Playlists / collections.
- Soft-delete with a trash/retention window before permanent deletion.

### Access & Sharing

- App-level authentication (needed before any public exposure).
- Public access via Cloudflare Tunnel, per the platform's networking model.
- Multi-user accounts with per-user libraries and permissions.
- Expiring share links for individual videos.

### Frontend

- Replace the v1 Jinja2/htmx templates with a React SPA against the existing
  JSON API (the API was designed from v1 to support this swap).
- PWA / installable app for mobile.

### Platform & Ops

- CI/CD: GitHub Actions building/testing/publishing the image to GHCR,
  registered with `macmini-lab`'s Argo CD application registry.
- Structured logging and metrics wired into the platform's shared
  Grafana/Loki/Prometheus stack.
- Integration tests against real Postgres/MinIO via Testcontainers.
- API-key auth and rate limiting on the JSON API (learning exercise in
  FastAPI security dependencies).
