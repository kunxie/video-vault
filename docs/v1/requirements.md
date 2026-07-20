# Video Vault Requirements

## Overview

Video Vault is a personal service for uploading, downloading, deleting, and
watching MP4 videos online. It runs on the `macmini-lab` platform
(single-node K3s), using its shared MinIO (storage) and Postgres (metadata),
deployed via the platform's GitOps registry. It's also a learning project —
see [`README.md`](../../README.md) for the future-ideas backlog.

## Design Principle

v1 stays minimal (see Non-Goals), but three choices are made now to avoid a
rewrite later: the API returns JSON (not just HTML, so a future React
frontend can swap in), uploads are checksummed (so future dedup/integrity
checks don't need a backfill), and storage uses MinIO's S3 API directly (so
future chunked/resumable upload only changes how objects are written).

## Goals

- Upload, download, delete, and watch MP4 videos online (in-browser,
  seekable playback).
- Fit the platform's constraints: no HA, no complex storage orchestration,
  single node.

## Non-Goals (v1)

- Resumable/chunked upload (single-request only).
- Transcoding, thumbnails, multiple renditions.
- Non-MP4 formats.
- Multi-user accounts, sharing, permissions.
- Search, tags, playlists.
- Public/unauthenticated exposure.
- Mobile apps.

## Users

Single user (the owner), over Tailscale only. No public access in v1.

## Functional Requirements

- **Upload**: single-request MP4 upload, streamed (not buffered) into MinIO;
  metadata (filename, size, content type, checksum, timestamp) in Postgres.
  20GB max per file, app-enforced.
- **List**: shown to support download/delete/watch.
- **Download**: stream the original file back unmodified.
- **Delete**: removes the MinIO object and Postgres record. Permanent.
- **Watch online**: HTTP range support for seek/scrub in the browser.

## Non-Functional Requirements

- **Storage**: platform's shared MinIO + Postgres — no new infra.
- **Auth**: none in v1; Tailscale-only reachability is the access control.
  Required before any public exposure.
- **Availability**: best-effort, single node, no HA.
- **Backups**: platform policy — weekly MinIO sync, daily Postgres backup,
  one remote copy.
- **Deployment**: own repo/image, registered via `macmini-lab`'s
  application-registry (`k8s/registry/video-vault/production.json`).
- **Scale**: tens to low hundreds of videos.
- **Stack**: Python, FastAPI, `boto3`, SQLAlchemy/Postgres.
- **Frontend**: server-rendered — Jinja2 + htmx, native `<video>` tag.

## Open Questions

None.
