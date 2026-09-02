# File Vault v2 — Product Requirements Document

**Status:** Draft 0.4

**Owner:** Kun Xie

**Last updated:** 2026-09-01

## 1. Overview

File Vault is a private, self-hosted service for preserving, organizing,
previewing, and retrieving personal files. It replaces the video-specific
Video Vault v1 with a unified library for photos, video, audio, PDFs, text,
documents, archives, and other files.

File Vault runs on the single-node `macmini-lab` platform. It uses MinIO for
file content, Postgres for metadata and relationships, and FastAPI for the
application and API.

### 1.1 Terms

- **Asset:** A user-visible library item with metadata and lifecycle state.
- **Original:** The immutable bytes accepted from the user.
- **Derivative:** Generated content, such as a thumbnail or playback rendition.
- **Logical duplicate:** A separate asset that references identical original
  content.
- **Operator:** The person who deploys and maintains File Vault.

## 2. Product Vision

File Vault provides a dependable private home for personal files: originals are
preserved, large transfers are resilient, supported formats are easy to
preview, and every asset remains searchable and downloadable.

> **Store broadly; preview selectively.**

Preview support is optional. Unknown or unsupported formats remain preserved,
searchable, and downloadable.

## 3. Problem Statement

Video Vault v1 validates the Postgres and MinIO storage path but is limited to
MP4 files and a video-specific data model. File Vault addresses these gaps:

- Personal files lack a unified private library.
- Large uploads cannot be paused or resumed after interruption.
- Filename-only browsing does not scale.
- File types require distinct metadata and preview behavior.
- Transfer and processing states are not visible.
- Duplicate content is not detected.
- Deletion is immediate and offers no recovery window.
- The current lifecycle and schema do not generalize beyond video.

## 4. Target User and Context

The primary user is the owner of `macmini-lab`, accessing File Vault from
trusted desktop and mobile browsers over the private Tailnet.

Assumptions:

- v2 has one user and one library.
- The user values file ownership, privacy, integrity, and recoverability.
- The library will contain up to several thousand assets; the final capacity
  target remains open.
- Files may be large and networks unreliable.
- Public access and collaboration are out of scope.
- Originals must remain unchanged and downloadable.

## 5. Product Principles

1. **Preserve originals.** Never silently replace or modify uploaded content.
2. **Prevent unexpected data loss.** Make destructive actions explicit and
   recoverable where practical.
3. **Store broadly; preview selectively.** Separate storage eligibility from
   preview support.
4. **Use one asset model.** Apply a consistent identity, lifecycle, integrity,
   and organization model to every file type.
5. **Design for interruption.** Make large transfers resumable.
6. **Expose system state.** Clearly report transfer, processing, and retention
   status.
7. **Treat uploads as untrusted.** Never execute or unsafely render uploaded
   content.
8. **Minimize operational burden.** Keep the service manageable by one operator.

## 6. Goals

Normative behavior is defined by the identified requirements in Sections
10–12. The product goals are to:

- Preserve and retrieve arbitrary allowed files without changing their bytes.
- Support observable, resumable large-file uploads.
- Verify integrity and detect duplicate content with SHA-256.
- Classify recognized formats and extract safe technical metadata.
- Preview approved formats without compromising the original.
- Provide responsive browsing, search, filtering, sorting, and organization.
- Report actionable transfer and processing failures.
- Provide recoverable deletion through a retention period.
- Migrate Video Vault v1 data safely.
- Remain supportable on `macmini-lab`.

## 7. Non-Goals

- Public or anonymous access.
- Multi-user accounts, profiles, sharing, or per-user permissions.
- Native mobile or desktop applications.
- Collaborative document editing.
- Editing or modifying original file content.
- Executing uploaded programs, scripts, macros, or archive contents.
- Automatically extracting compressed archives.
- Rich in-browser previews for every accepted file format.
- Full-text indexing of every document and archive format.
- Optical character recognition (OCR).
- AI-generated descriptions, classification, or facial recognition.
- Digital-rights management (DRM).
- High availability or multi-node failover.

These exclusions apply only to the initial v2 release.

## 8. File-Type Scope

### 8.1 Capability Levels

File Vault defines three capability levels:

1. **Stored:** Preserve, verify, organize, download, trash, restore, and delete
   the original.
2. **Inspected:** Identify the format and extract safe technical metadata.
3. **Previewable:** Provide a safe browser preview or playback experience.

Inspection or preview failure does not affect access to a verified original.

### 8.2 Initial File-Family Experience

| File family | Example formats | Stored | Initial experience |
| --- | --- | --- | --- |
| Photos | JPEG, PNG, WebP, GIF | Yes | Metadata, thumbnail, preview |
| Video | MP4, WebM; other approved inputs | Yes | Metadata, thumbnail, compatible playback |
| Audio | MP3, M4A, AAC, FLAC, WAV, OGG | Yes | Metadata, compatible playback |
| PDF | PDF | Yes | Metadata, first-page thumbnail, preview |
| Text | TXT, Markdown, JSON, CSV, logs | Yes | Size-limited, read-only preview |
| Documents | DOCX, XLSX, PPTX, ODT | Yes | Metadata and download |
| Archives | ZIP, TAR, TAR.GZ, 7z | Yes | Metadata and download; no extraction |
| Other | Any allowed format | Yes | Generic metadata and download |

The launch format matrix and browser requirements remain open. Listing a
container format does not guarantee support for every embedded codec.

## 9. Key User Workflows

### 9.1 Upload

Select or drop files, monitor per-file progress, and resume interrupted
transfers. Verified originals appear in the library while processing continues.

### 9.2 Resolve Duplicates

Identify matching content by checksum and let the user skip it or retain another
logical asset without silently duplicating storage.

### 9.3 Browse and Search

Browse thumbnails or file-type icons; search metadata; and filter or sort by
family, date, size, and state.

### 9.4 Preview and Play

Open supported content in a safe, format-appropriate viewer. For unsupported
formats, show metadata and download instead of a broken preview.

### 9.5 Inspect and Organize

Review technical and lifecycle metadata; edit user-managed metadata; and apply
tags or collections without modifying the original.

### 9.6 Download Originals

Download the unmodified original with a safe filename and verifiable checksum.

### 9.7 Delete and Restore

Move an asset to trash, restore it during retention, or explicitly delete its
unshared content permanently.

### 9.8 Recover from Failures

Identify the failed stage and retry or discard eligible work without creating
duplicate records or orphaned objects.

## 10. Functional Requirements

### 10.1 Requirement Language

Each requirement has a stable identifier. IDs must not be reused; removed
requirements remain recorded as retired rather than being assigned a new
meaning.

- **MUST** indicates required initial-v2 behavior.
- **SHOULD** indicates expected behavior that may be deferred only with an
  explicit product decision.
- **MAY** indicates optional behavior that does not define release readiness.
- **TBD** marks a value that must be resolved before acceptance testing.

### 10.2 Asset Identity and Lifecycle

- **FR-ASSET-001 — MUST:** File Vault shall assign every accepted asset a
  globally unique, stable identifier independent of its filename and storage
  location.
- **FR-ASSET-002 — MUST:** File Vault shall preserve the original filename as
  metadata without using it as the object-storage identity.
- **FR-ASSET-003 — MUST:** File Vault shall record the original object's storage
  key, byte size, cryptographic checksum, upload timestamp, user-reported
  content type, detected content type, and file family.
- **FR-ASSET-004 — MUST:** File Vault shall represent an asset's storage,
  processing, and retention lifecycles independently, so a failure in one
  lifecycle does not hide the state of the others.
- **FR-ASSET-005 — MUST:** File Vault shall retain enough state to distinguish a
  failed upload from a safely stored original whose required or optional
  processing failed.
- **FR-ASSET-006 — MUST:** Every derived object shall reference the asset and
  processing operation that produced it.
- **FR-ASSET-007 — MUST:** Derived objects shall never replace or mutate the
  original object.
- **FR-ASSET-008 — MUST:** An inspection or preview failure shall not prevent
  download of a verified original.
- **FR-ASSET-009 — MUST:** File Vault shall display the current lifecycle and
  preview-availability states to the user.
- **FR-ASSET-010 — SHOULD:** File Vault should retain a timestamped history of
  significant lifecycle transitions.
- **FR-ASSET-011 — MUST:** Storage state `uploading` shall mean that the original
  is still being transferred and has not yet been accepted as durably stored.
- **FR-ASSET-012 — MUST:** Storage state `stored` shall mean that the complete
  original exists in MinIO, its expected size and SHA-256 checksum have been
  verified, and its required Postgres metadata is durable.
- **FR-ASSET-013 — MUST:** Storage state `failed` shall mean that File Vault
  could not complete or verify storage of the original; it shall not imply that
  a complete downloadable original is available.
- **FR-ASSET-014 — MUST:** Processing state `pending` shall mean that the
  original is stored and one or more required inspection or derivative jobs have
  not started.
- **FR-ASSET-015 — MUST:** Processing state `processing` shall mean that at least
  one required inspection or derivative job is running.
- **FR-ASSET-016 — MUST:** Processing state `ready` shall mean that all required
  inspection and derivative work for the detected file type has completed
  successfully.
- **FR-ASSET-017 — MUST:** Processing state `partially_ready` shall mean that the
  asset's required baseline experience is available but one or more optional
  derivatives or metadata operations failed or remain unavailable.
- **FR-ASSET-018 — MUST:** Processing state `failed` shall mean that required
  inspection or derivative work failed; it shall not invalidate or prevent
  download of an original whose storage state is `stored`.
- **FR-ASSET-019 — MUST:** Processing state `unsupported` shall mean that File
  Vault safely stored the original but has no approved inspection or preview
  pipeline for its detected type.
- **FR-ASSET-020 — MUST:** Retention state `active` shall mean that the asset is
  part of the normal library and is not scheduled for permanent deletion.
- **FR-ASSET-021 — MUST:** Retention state `trashed` shall mean that the asset is
  hidden from the normal library, retains its original, derivatives, metadata,
  tags, and collection memberships, and can be restored before its purge time.
- **FR-ASSET-022 — MUST:** Retention state `deleting` shall mean that permanent
  deletion has started, restoration and conflicting mutations are blocked, and
  File Vault is removing exclusively owned metadata and MinIO objects.
- **FR-ASSET-023 — MUST:** Retention state `deletion_failed` shall mean that
  permanent deletion completed only partially or could not be verified; the
  asset shall remain hidden and discoverable to operators for safe retry or
  reconciliation.
- **FR-ASSET-024 — MUST:** Retention state `deleted` shall be terminal and shall
  mean that exclusively owned originals, derivatives, and user metadata have
  been removed, while only the minimum required deletion audit record remains.

The three dimensions may coexist. For example:

```text
storage_state    = stored
processing_state = failed
retention_state  = active
```

This combination means that the verified original is safe and downloadable,
but required preview processing failed. The primary expected transitions are:

```text
Storage:    uploading ──> stored
                 └──────> failed

Processing: pending ──> processing ──> ready
                            ├─────────> partially_ready
                            └─────────> failed
             pending ─────────────────> unsupported

Retention:  active ──> trashed ──> deleting ──> deleted
                <──── restored       └────────> deletion_failed
                                         retry ──> deleting
```

### 10.3 Upload

- **FR-UPLOAD-001 — MUST:** The user shall be able to select one or multiple
  files for upload through a supported browser.
- **FR-UPLOAD-002 — MUST:** The user shall be able to add files through both a
  file picker and drag-and-drop on supported devices.
- **FR-UPLOAD-003 — MUST:** File Vault shall show independent progress and state
  for every file in a multi-file upload.
- **FR-UPLOAD-004 — MUST:** File Vault shall support resumable multipart upload
  for files at or above a configurable threshold.
- **FR-UPLOAD-005 — MUST:** A resumable upload shall continue from already
  acknowledged parts after a recoverable network interruption.
- **FR-UPLOAD-006 — MUST:** An upload session shall have a stable identity and
  shall record its asset, expected size, received parts, state, creation time,
  and expiry time.
- **FR-UPLOAD-007 — MUST:** File Vault shall prevent an upload from exceeding
  the configured maximum individual file size.
- **FR-UPLOAD-008 — MUST:** File Vault shall prevent new uploads when a
  configured storage or library quota would be exceeded.
- **FR-UPLOAD-009 — MUST:** File Vault shall reject completion when the received
  byte count differs from the declared file size.
- **FR-UPLOAD-010 — MUST:** File Vault shall verify that all required parts are
  present before completing a multipart upload.
- **FR-UPLOAD-011 — MUST:** File Vault shall calculate or verify a SHA-256
  checksum for the completed original.
- **FR-UPLOAD-012 — MUST:** An asset shall not enter the `stored` state until
  its completed original object and required metadata have been verified.
- **FR-UPLOAD-013 — MUST:** The user shall be able to cancel an active upload.
- **FR-UPLOAD-014 — MUST:** Cancelling an upload shall schedule its incomplete
  multipart data for cleanup.
- **FR-UPLOAD-015 — MUST:** Expired incomplete multipart uploads shall be
  aborted automatically.
- **FR-UPLOAD-016 — MUST:** The UI shall report successful, cancelled, failed,
  duplicate, and expired upload outcomes separately.
- **FR-UPLOAD-017 — MUST:** A failed file in a batch shall not cancel unrelated
  successful file uploads.
- **FR-UPLOAD-018 — SHOULD:** The user should be able to retry a failed or
  expired upload without selecting unrelated batch files again.
- **FR-UPLOAD-019 — SHOULD:** The upload UI should estimate remaining transfer
  time when enough progress information is available.
- **FR-UPLOAD-020 — MAY:** The user may pause and manually resume an active
  multipart upload.

### 10.4 File Classification

- **FR-TYPE-001 — MUST:** File Vault shall accept arbitrary file types for
  storage unless a configured security or operational policy explicitly blocks
  them.
- **FR-TYPE-002 — MUST:** File Vault shall treat the browser-provided content
  type and filename extension as untrusted metadata.
- **FR-TYPE-003 — MUST:** File Vault shall attempt to detect a stored file's
  content type from its content using a maintained detection mechanism.
- **FR-TYPE-004 — MUST:** File Vault shall record both the reported and detected
  content types when available.
- **FR-TYPE-005 — MUST:** File Vault shall assign every asset to a supported
  file family or to `other` when it cannot be classified.
- **FR-TYPE-006 — MUST:** A failure to recognize a file type shall not prevent
  storage and download when the file is otherwise allowed.
- **FR-TYPE-007 — MUST:** Preview eligibility shall be determined by detected
  format and safety policy, not solely by extension.
- **FR-TYPE-008 — MUST:** File Vault shall not execute uploaded files, scripts,
  macros, or archive contents.
- **FR-TYPE-009 — MUST:** File Vault shall not automatically extract uploaded
  archives.
- **FR-TYPE-010 — SHOULD:** File Vault should expose the reason when policy
  blocks an upload or preview.

### 10.5 Duplicate Detection

- **FR-DUP-001 — MUST:** File Vault shall detect duplicate original content by
  SHA-256 checksum rather than filename.
- **FR-DUP-002 — MUST:** File Vault shall report an existing matching asset when
  a duplicate is detected and the existing asset is visible to the user.
- **FR-DUP-003 — MUST:** The user shall be able to skip storage of a detected
  duplicate.
- **FR-DUP-004 — MUST:** The user shall be able to intentionally retain a second
  logical asset that references the same content.
- **FR-DUP-005 — MUST:** Duplicate handling shall not silently overwrite the
  existing asset's metadata.
- **FR-DUP-006 — SHOULD:** File Vault should avoid storing a second physical
  copy when multiple logical assets intentionally reference identical content.
- **FR-DUP-007 — SHOULD:** The UI should distinguish exact content duplicates
  from filename collisions.

### 10.6 Metadata

- **FR-META-001 — MUST:** File Vault shall preserve immutable technical metadata
  separately from user-editable metadata.
- **FR-META-002 — MUST:** The user shall be able to set and edit an asset title.
- **FR-META-003 — MUST:** The user shall be able to set and edit an asset
  description.
- **FR-META-004 — MUST:** Metadata extraction shall run asynchronously after the
  original is verified when extraction is supported.
- **FR-META-005 — MUST:** File Vault shall record the extractor name and version
  associated with extracted metadata.
- **FR-META-006 — MUST:** Reprocessing shall replace or version derived
  technical metadata without modifying user-managed metadata.
- **FR-META-007 — MUST:** Photo inspection shall extract dimensions and
  orientation when available.
- **FR-META-008 — MUST:** Video inspection shall extract duration, dimensions,
  container, and codec information when available.
- **FR-META-009 — MUST:** Audio inspection shall extract duration, codec, and
  available embedded title, artist, album, and track metadata.
- **FR-META-010 — MUST:** PDF inspection shall extract page count and available
  document metadata.
- **FR-META-011 — MUST:** Text inspection shall detect encoding or report that a
  safe text preview cannot be produced.
- **FR-META-012 — SHOULD:** Archive inspection should record the archive format
  and entry count without extracting entry contents to persistent storage.
- **FR-META-013 — SHOULD:** The user should be able to request re-inspection of a
  stored asset.
- **FR-META-014 — SHOULD:** File Vault should preserve relevant original capture
  or creation timestamps separately from upload time.

### 10.7 Library and Search

- **FR-LIB-001 — MUST:** File Vault shall provide a paginated or equivalently
  bounded library view.
- **FR-LIB-002 — MUST:** The default library view shall exclude trashed assets.
- **FR-LIB-003 — MUST:** Each library item shall show its title or original
  filename, file family, size, and upload date.
- **FR-LIB-004 — MUST:** Each library item shall show an available thumbnail or
  a recognizable file-family fallback icon.
- **FR-LIB-005 — MUST:** The user shall be able to search by title and original
  filename.
- **FR-LIB-006 — MUST:** Search shall be case-insensitive for text fields where
  language rules permit.
- **FR-LIB-007 — MUST:** The user shall be able to filter by file family.
- **FR-LIB-008 — MUST:** The user shall be able to filter by lifecycle or
  processing state.
- **FR-LIB-009 — MUST:** The user shall be able to sort by upload date,
  filename, and file size in ascending or descending order.
- **FR-LIB-010 — MUST:** Search, filter, sort, and pagination selections shall
  compose without returning contradictory UI state.
- **FR-LIB-011 — MUST:** The user shall be able to open an asset-detail view
  from the library.
- **FR-LIB-012 — MUST:** Empty, loading, failed, and no-search-results states
  shall be presented distinctly.
- **FR-LIB-013 — SHOULD:** The library should preserve the user's current query
  and position when returning from an asset detail view.
- **FR-LIB-014 — SHOULD:** The user should be able to filter by upload or
  original-content date range.
- **FR-LIB-015 — SHOULD:** Search should include descriptions, tags, and
  collection names.

### 10.8 Organization

- **FR-ORG-001 — MUST:** The user shall be able to create, rename, and delete
  tags.
- **FR-ORG-002 — MUST:** The user shall be able to assign and remove multiple
  tags on an asset.
- **FR-ORG-003 — MUST:** Deleting a tag shall not delete its assets.
- **FR-ORG-004 — MUST:** The user shall be able to create, rename, and delete
  collections.
- **FR-ORG-005 — MUST:** The user shall be able to add an asset to multiple
  collections and remove it from a collection.
- **FR-ORG-006 — MUST:** Deleting a collection shall not delete its assets.
- **FR-ORG-007 — MUST:** Tags and collections shall support all file families.
- **FR-ORG-008 — MUST:** The user shall be able to filter the library by tag or
  collection.
- **FR-ORG-009 — SHOULD:** The user should be able to apply tags or collection
  membership to multiple selected assets.
- **FR-ORG-010 — MAY:** A collection may support an explicit user-defined item
  order.

### 10.9 Preview and Playback

- **FR-PREVIEW-001 — MUST:** File Vault shall explicitly report whether an asset
  is previewable, still processing, unsupported, or failed.
- **FR-PREVIEW-002 — MUST:** Preview generation shall produce derived objects
  separate from the original.
- **FR-PREVIEW-003 — MUST:** The user shall be able to retry failed preview
  generation when the failure is retryable.
- **FR-PREVIEW-004 — MUST:** Unsupported assets shall provide metadata and a
  download action without attempting inline rendering.
- **FR-PREVIEW-005 — MUST:** Image preview shall preserve aspect ratio.
- **FR-PREVIEW-006 — MUST:** File Vault shall generate image thumbnails without
  requiring the library view to download full-resolution originals.
- **FR-PREVIEW-007 — MUST:** Animated images shall not autoplay indefinitely in
  the library grid.
- **FR-PREVIEW-008 — MUST:** Supported video assets shall provide browser
  playback with standard play, pause, volume, fullscreen, and seek controls.
- **FR-PREVIEW-009 — MUST:** Supported audio assets shall provide browser
  playback with standard play, pause, volume, and seek controls.
- **FR-PREVIEW-010 — MUST:** Compatible media streaming shall support HTTP byte
  ranges.
- **FR-PREVIEW-011 — MUST:** File Vault shall generate a representative
  thumbnail for supported video files.
- **FR-PREVIEW-012 — MUST:** File Vault shall generate a first-page thumbnail
  for supported PDF files.
- **FR-PREVIEW-013 — MUST:** PDF preview shall be isolated so active document
  content cannot execute with File Vault origin privileges.
- **FR-PREVIEW-014 — MUST:** Text preview shall be read-only and escaped before
  display.
- **FR-PREVIEW-015 — MUST:** Text preview shall read no more than a configurable
  byte limit from the original.
- **FR-PREVIEW-016 — MUST:** Truncated text preview shall be visibly identified
  as truncated.
- **FR-PREVIEW-017 — MUST:** Office documents and archives shall initially use
  metadata and download experiences without rich inline preview.
- **FR-PREVIEW-018 — SHOULD:** The user should be able to request regeneration
  of a missing or stale derivative.
- **FR-PREVIEW-019 — MAY:** File Vault may transcode incompatible audio or video
  into a browser-compatible derived rendition.
- **FR-PREVIEW-020 — MAY:** File Vault may generate adaptive-bitrate video
  renditions after a separate scope decision.

### 10.10 Playback Progress

- **FR-PLAY-001 — MUST:** File Vault shall record playback position for video
  and audio assets.
- **FR-PLAY-002 — MUST:** Playback progress shall be associated with the asset
  and current single-user library.
- **FR-PLAY-003 — MUST:** Reopening partially consumed media shall offer to
  resume near the last meaningful position.
- **FR-PLAY-004 — MUST:** Completing media or reaching a configurable end
  threshold shall mark it completed rather than resuming at the final frame.
- **FR-PLAY-005 — MUST:** The user shall be able to restart playback from the
  beginning.
- **FR-PLAY-006 — SHOULD:** Progress updates should be rate-limited while
  preserving recent position during normal browser closure or navigation.
- **FR-PLAY-007 — SHOULD:** The library should visually distinguish unwatched,
  in-progress, and completed media.

### 10.11 Asset Details and Downloads

- **FR-DETAIL-001 — MUST:** The asset-detail view shall show original filename,
  byte size, detected type, file family, checksum, upload time, lifecycle state,
  and preview state.
- **FR-DETAIL-002 — MUST:** The detail view shall distinguish extracted metadata
  from user-editable metadata.
- **FR-DOWNLOAD-001 — MUST:** The user shall be able to download the unmodified
  original for every verified stored asset.
- **FR-DOWNLOAD-002 — MUST:** A download response shall use a safely encoded
  version of the original filename.
- **FR-DOWNLOAD-003 — MUST:** Download shall support streaming without buffering
  the complete object in application memory.
- **FR-DOWNLOAD-004 — MUST:** Downloading a derived preview shall never be
  presented as downloading the original.
- **FR-DOWNLOAD-005 — SHOULD:** Original downloads should support resumable byte
  ranges when the client requests them.
- **FR-DOWNLOAD-006 — SHOULD:** The user should be able to view or copy the
  original's SHA-256 checksum.

### 10.12 Deletion and Recovery

- **FR-TRASH-001 — MUST:** The user shall be able to move an active asset to
  trash.
- **FR-TRASH-002 — MUST:** Trashing an asset shall hide it from the default
  library without immediately deleting its objects.
- **FR-TRASH-003 — MUST:** File Vault shall provide a dedicated trash view.
- **FR-TRASH-004 — MUST:** The trash view shall show when each asset is scheduled
  for permanent deletion.
- **FR-TRASH-005 — MUST:** The default retention period shall be 30 days and
  shall be configurable by the operator.
- **FR-TRASH-006 — MUST:** The user shall be able to restore an asset before
  permanent deletion begins.
- **FR-TRASH-007 — MUST:** Restoration shall preserve user-managed metadata,
  tags, collection membership, and available derivatives.
- **FR-TRASH-008 — MUST:** File Vault shall automatically schedule expired trash
  items for permanent deletion.
- **FR-TRASH-009 — MUST:** The user shall be able to request permanent deletion
  of an individual trashed asset before expiry through an explicit confirmation.
- **FR-TRASH-010 — MUST:** Permanent deletion shall remove the original and all
  derivatives when they are no longer referenced by another logical asset.
- **FR-TRASH-011 — MUST:** A partial deletion failure shall remain recorded and
  eligible for safe retry or reconciliation.
- **FR-TRASH-012 — SHOULD:** The user should be able to empty all trash through
  an explicit confirmation that communicates irreversibility.

### 10.13 Background Jobs and Reconciliation

- **FR-JOB-001 — MUST:** Metadata inspection, thumbnail generation, and other
  expensive derivatives shall run outside the interactive request lifecycle.
- **FR-JOB-002 — MUST:** Every background job shall record its type, asset,
  state, attempt count, timestamps, and last failure information.
- **FR-JOB-003 — MUST:** Retrying a job shall not create duplicate active
  derivatives or corrupt the original.
- **FR-JOB-004 — MUST:** File Vault shall enforce a configurable retry limit and
  backoff policy for retryable work.
- **FR-JOB-005 — MUST:** Non-retryable and exhausted failures shall be visible to
  the user or operator as appropriate.
- **FR-RECON-001 — MUST:** File Vault shall provide an operator-invoked
  reconciliation operation for Postgres metadata and MinIO objects.
- **FR-RECON-002 — MUST:** Reconciliation shall detect missing originals,
  missing derivatives, unreferenced managed objects, incomplete multipart
  uploads, and inconsistent lifecycle state.
- **FR-RECON-003 — MUST:** Reconciliation shall support a report-only mode that
  does not mutate data.
- **FR-RECON-004 — MUST:** Destructive reconciliation actions shall require an
  explicit mode and shall produce an audit record.
- **FR-RECON-005 — SHOULD:** Reconciliation should be resumable and safe to run
  repeatedly.

### 10.14 Operator Configuration

- **FR-CONFIG-001 — MUST:** The operator shall be able to configure maximum file
  size, total library quota, multipart threshold, upload-session expiry, trash
  retention, text-preview limit, and processing concurrency.
- **FR-CONFIG-002 — MUST:** Invalid or internally inconsistent required
  configuration shall prevent readiness and produce an actionable error.
- **FR-CONFIG-003 — MUST:** Secrets shall be supplied independently from
  non-secret configuration.
- **FR-CONFIG-004 — SHOULD:** The operator should be able to configure blocked
  file types and preview eligibility without modifying stored asset metadata.
- **FR-CONFIG-005 — SHOULD:** Operational configuration changes should not
  require rebuilding the application image.

## 11. Non-Functional Requirements

### 11.1 Integrity

- **NFR-INT-001 — MUST:** Original object keys shall be generated by File Vault
  and shall not contain an untrusted path derived directly from a filename.
- **NFR-INT-002 — MUST:** An independently calculated SHA-256 checksum of a
  downloaded original shall match the checksum recorded for that original.
- **NFR-INT-003 — MUST:** File Vault shall not report an asset as safely stored
  unless both the original object and required metadata are durably available.
- **NFR-INT-004 — MUST:** Operations spanning Postgres and MinIO shall have a
  defined partial-failure state and reconciliation path.
- **NFR-INT-005 — MUST:** Retried completion, processing, trash, restoration,
  and deletion operations shall be idempotent or detect prior completion.
- **NFR-INT-006 — MUST:** Concurrent updates shall not silently discard newer
  user-managed metadata.
- **NFR-INT-007 — MUST:** Shared physical content shall not be deleted while any
  active logical asset still references it.
- **NFR-INT-008 — SHOULD:** File Vault should support scheduled integrity
  verification of stored originals without requiring download through the UI.

### 11.2 Performance and Capacity

- **NFR-PERF-001 — MUST:** Uploading or downloading a file shall use bounded
  application memory independent of total file size.
- **NFR-PERF-002 — MUST:** At the supported collection size, the first page of
  the default library shall return within **TBD milliseconds at p95**, excluding
  client network latency.
- **NFR-PERF-003 — MUST:** At the supported collection size, a normal metadata
  search shall return within **TBD milliseconds at p95**, excluding client
  network latency.
- **NFR-PERF-004 — MUST:** File Vault shall support files up to **TBD GiB**.
- **NFR-PERF-005 — MUST:** File Vault shall support at least **TBD assets** and
  **TBD TiB** of managed original content.
- **NFR-PERF-006 — MUST:** File Vault shall support **TBD concurrent uploads**
  without violating integrity or memory requirements.
- **NFR-PERF-007 — MUST:** Supported locally reachable media shall begin
  playback within **TBD seconds at p95** under the defined test conditions.
- **NFR-PERF-008 — MUST:** A supported asset shall receive required initial
  metadata and thumbnail processing within **TBD minutes at p95** under the
  defined workload.
- **NFR-PERF-009 — SHOULD:** Library thumbnails should use derivatives sized for
  their display context instead of full originals.
- **NFR-PERF-010 — SHOULD:** Pagination limits shall prevent response size from
  increasing linearly with total library size.

### 11.3 Reliability and Recovery

- **NFR-REL-001 — MUST:** A process restart during upload or background
  processing shall not mark incomplete work successful.
- **NFR-REL-002 — MUST:** Resumable upload state acknowledged to the client shall
  survive an application-process restart.
- **NFR-REL-003 — MUST:** Background work shall use bounded retries and shall not
  retry permanent failures indefinitely.
- **NFR-REL-004 — MUST:** A MinIO or Postgres outage shall produce a controlled
  unavailable or failed state rather than silent data loss.
- **NFR-REL-005 — MUST:** File Vault shall recover safely after an ungraceful
  application restart without manual database edits.
- **NFR-REL-006 — MUST:** Permanent deletion failures shall remain discoverable
  until resolved or explicitly acknowledged by an operator.
- **NFR-REL-007 — SHOULD:** Scheduled cleanup and reconciliation jobs should
  resume without repeating completed destructive actions after interruption.
- **NFR-REL-008 — SHOULD:** Recovery procedures should define expected behavior
  when Postgres and MinIO are restored to different points in time.

### 11.4 Security and Privacy

- **NFR-SEC-001 — MUST:** Initial v2 production access shall be restricted to
  the private Tailnet.
- **NFR-SEC-002 — MUST:** File Vault shall not expose a public ingress in the
  initial v2 deployment.
- **NFR-SEC-003 — MUST:** User-controlled filenames and metadata shall be encoded
  or escaped for every HTML, HTTP-header, log, and query context in which they
  appear.
- **NFR-SEC-004 — MUST:** Active uploaded content shall not be served with File
  Vault application-origin privileges unless it has been transformed into an
  explicitly safe derivative.
- **NFR-SEC-005 — MUST:** Text and structured-data previews shall render as inert
  text rather than interpreted HTML or script.
- **NFR-SEC-006 — MUST:** PDF preview shall be sandboxed or isolated from the
  File Vault application origin.
- **NFR-SEC-007 — MUST:** Storage and database credentials shall come from
  platform-managed secrets and shall not be committed to source control or
  included in logs.
- **NFR-SEC-008 — MUST:** Communication with MinIO and Postgres shall follow the
  private platform network and transport-security policy.
- **NFR-SEC-009 — MUST:** API operations shall validate resource identifiers and
  shall not permit user-controlled object keys.
- **NFR-SEC-010 — MUST:** Error responses shall not expose credentials, internal
  connection strings, object-store signatures, or stack traces.
- **NFR-SEC-011 — MUST:** Presigned transfer operations, if used, shall be
  time-limited and scoped to the required object and operation.
- **NFR-SEC-012 — MUST:** Logs shall avoid file contents and shall minimize
  sensitive personal metadata.
- **NFR-SEC-013 — SHOULD:** File inspection libraries and media tools should run
  with least privilege and bounded CPU, memory, file, and execution time.
- **NFR-SEC-014 — SHOULD:** The operator should be able to revoke an active
  upload session.
- **NFR-SEC-015 — MUST:** Application authentication and authorization shall be
  implemented before access expands beyond the Tailnet.

### 11.5 Accessibility and Responsive Design

- **NFR-A11Y-001 — MUST:** Upload, library, search, asset detail, preview,
  download, trash, and restore flows shall be operable by keyboard.
- **NFR-A11Y-002 — MUST:** Interactive controls shall have accessible names and
  visible focus indicators.
- **NFR-A11Y-003 — MUST:** Status, progress, errors, and file families shall not
  be communicated by color alone.
- **NFR-A11Y-004 — MUST:** Text and essential controls shall meet WCAG 2.2 AA
  color-contrast requirements.
- **NFR-A11Y-005 — MUST:** The interface shall remain usable at 200% browser
  zoom without loss of core functionality.
- **NFR-A11Y-006 — MUST:** Meaningful generated images shall have appropriate
  alternatives; decorative thumbnails shall not create redundant screen-reader
  output.
- **NFR-A11Y-007 — MUST:** Upload and processing progress changes shall be
  available to assistive technology without excessive announcements.
- **NFR-A11Y-008 — MUST:** Core workflows shall work at supported mobile and
  desktop viewport widths without horizontal page scrolling.
- **NFR-A11Y-009 — SHOULD:** Motion and autoplay behavior should respect reduced
  motion and user playback preferences.

### 11.6 Browser Compatibility

- **NFR-COMPAT-001 — MUST:** Before release, File Vault shall document the
  supported versions of Chrome, Firefox, Safari, and Edge on applicable desktop
  and mobile platforms.
- **NFR-COMPAT-002 — MUST:** Core storage and download workflows shall function
  on every supported browser even when a particular preview codec is absent.
- **NFR-COMPAT-003 — MUST:** Preview compatibility limitations shall be reported
  as unsupported preview rather than as loss or corruption of the asset.
- **NFR-COMPAT-004 — SHOULD:** The UI should use progressive enhancement where a
  browser lacks an optional convenience capability such as drag-and-drop.

### 11.7 Observability and Auditability

- **NFR-OBS-001 — MUST:** Application and worker logs shall be structured and
  include timestamp, severity, service component, event name, and relevant safe
  identifiers.
- **NFR-OBS-002 — MUST:** A correlation identifier shall connect relevant upload
  session, asset, storage, and background-job events.
- **NFR-OBS-003 — MUST:** File Vault shall expose metrics for upload outcomes and
  bytes, job outcomes and duration, preview outcomes, API errors and latency,
  reconciliation findings, and deletion backlog.
- **NFR-OBS-004 — MUST:** Metrics labels shall avoid unbounded values such as
  filenames, asset IDs, and upload-session IDs.
- **NFR-OBS-005 — MUST:** Liveness checks shall report whether the application
  process can serve requests without requiring all dependencies to be healthy.
- **NFR-OBS-006 — MUST:** Readiness checks shall reflect whether required
  dependencies and configuration permit safe service.
- **NFR-OBS-007 — MUST:** Operators shall be able to identify failed uploads,
  processing, reconciliation, and deletion without manually querying tables.
- **NFR-OBS-008 — MUST:** Destructive administrative and reconciliation actions
  shall create an audit record with action, target, outcome, and timestamp.
- **NFR-OBS-009 — SHOULD:** Alerts should cover sustained readiness failure,
  repeated job failures, storage-capacity risk, reconciliation findings, and a
  growing deletion backlog.

### 11.8 Backup and Restore

- **NFR-BACKUP-001 — MUST:** Production backups shall cover Postgres metadata and
  MinIO originals and derivatives under a documented policy.
- **NFR-BACKUP-002 — MUST:** Backup documentation shall state retention,
  frequency, off-host copy behavior, expected RPO, and expected RTO.
- **NFR-BACKUP-003 — MUST:** The release shall document a coordinated restore
  procedure for Postgres and MinIO.
- **NFR-BACKUP-004 — MUST:** A restore exercise shall verify that restored asset
  metadata resolves to downloadable originals with matching checksums for a
  representative sample.
- **NFR-BACKUP-005 — MUST:** Backup credentials and remote copies shall follow
  the platform secret and access-control policy.
- **NFR-BACKUP-006 — SHOULD:** Restore exercises should occur on a documented
  recurring schedule.
- **NFR-BACKUP-007 — SHOULD:** Derived objects should be reproducible from
  originals where practical, even if they remain included in normal backups.

### 11.9 Maintainability, Testing, and Deployment

- **NFR-MAINT-001 — MUST:** File-family inspection and preview behavior shall be
  modular so support can be added without changing the core asset lifecycle.
- **NFR-MAINT-002 — MUST:** Database schema changes shall use versioned,
  repeatable migrations with automated upgrade testing from the last supported
  production version.
- **NFR-MAINT-003 — MUST:** Automated tests shall cover core lifecycle,
  access-control boundary, upload, checksum, duplicate, preview safety,
  download, trash, restoration, deletion, and reconciliation behavior.
- **NFR-MAINT-004 — MUST:** Integration tests shall exercise supported Postgres
  and S3-compatible storage behavior rather than relying exclusively on mocks.
- **NFR-MAINT-005 — MUST:** The build shall run formatting, linting, static type
  checking, tests, and migration validation before release.
- **NFR-MAINT-006 — MUST:** Production images shall be immutable and identified
  by a unique version or digest.
- **NFR-MAINT-007 — MUST:** Runtime containers shall run without root privileges
  unless a separately documented component requires otherwise.
- **NFR-MAINT-008 — MUST:** Deployment shall follow the `macmini-lab`
  application-registry and reviewed GitOps boundary.
- **NFR-MAINT-009 — MUST:** Operator documentation shall cover installation,
  configuration, upgrade, rollback, reconciliation, backup restore, and common
  failures.
- **NFR-MAINT-010 — SHOULD:** Dependency updates should be automated and gated by
  the required verification suite.
- **NFR-MAINT-011 — SHOULD:** File processors should expose their versions so
  assets can be identified for reprocessing after material upgrades.

## 12. Migration

- **MIG-001 — MUST:** Migration shall preserve every valid Video Vault v1
  original object without re-encoding or modifying its bytes.
- **MIG-002 — MUST:** Migration shall preserve each v1 original filename, byte
  size, content type, checksum, and upload timestamp when available.
- **MIG-003 — MUST:** Every migrated v1 video shall be represented as a File
  Vault asset with a stable mapping back to its v1 identity.
- **MIG-004 — MUST:** Migration shall detect and report missing objects, missing
  records, checksum mismatches, invalid metadata, and duplicate mappings.
- **MIG-005 — MUST:** Migration shall be safely resumable or repeatable without
  producing duplicate File Vault assets.
- **MIG-006 — MUST:** Migration shall support a validation-only mode that makes
  no production data changes.
- **MIG-007 — MUST:** v1 data shall remain recoverable until the v2 migration and
  production verification criteria have passed.
- **MIG-008 — MUST:** The migration run shall produce counts of examined,
  migrated, skipped, failed, and verified records and objects.
- **MIG-009 — MUST:** Migrated originals shall be checked against their stored v1
  SHA-256 checksums before migration is accepted.
- **MIG-010 — MUST:** The release shall define and exercise a production cutover
  and recovery procedure.
- **MIG-011 — MUST:** The procedure shall define how uploads and mutations are
  prevented or reconciled during the final migration window.
- **MIG-012 — MUST:** v1 retirement shall occur only after File Vault can list,
  preview or play where supported, and download the migrated sample set.
- **MIG-013 — SHOULD:** Migration should reuse existing MinIO originals in place
  when doing so preserves rollback safety and storage ownership boundaries.
- **MIG-014 — SHOULD:** Migration failures should be correctable and retryable at
  the individual-asset level.

Detailed migration mechanics belong in architecture and implementation
documents rather than this PRD.

## 13. Success Measures

Concrete targets will be set after scale and platform measurements are agreed.
The product should measure:

- Upload completion rate, excluding explicit user cancellations.
- Successful recovery rate for interrupted uploads.
- Time from completed upload to a browsable and, where supported, previewable
  asset.
- Preview and playback success rates for supported formats.
- Search and library response times at the supported collection size.
- Percentage of migrated v1 originals verified successfully.
- Count and age of unreconciled database records or storage objects.
- Successful restoration of assets during the trash retention window.

## 14. Open Decisions

1. Which file types, if any, should operational policy block from storage?
2. What are the exact inspected and previewable formats for the initial release?
3. Should incompatible video and audio be transcoded in v2, and should video use
   adaptive streaming renditions?
4. Which metadata fields should become mandatory search targets beyond title
   and filename?
5. What are the maximum file size, total asset count, total library size,
   concurrent-upload target, and performance acceptance values?
6. Should File Vault require application authentication even while it remains
   Tailnet-only?
7. Which office-document formats, if any, need rich preview rather than storage
   and download only?
8. When should the repository and deployment identity change from
   `video-vault` to `file-vault`?

## 15. Release Criteria

File Vault v2 is complete when:

- Every `MUST` requirement is satisfied or has an approved exception.
- The approved format matrix passes acceptance testing.
- Migrated Video Vault assets are available and verified.
- Backup, restore, migration recovery, and reconciliation procedures have been
  exercised.
- All unresolved `TBD` values have approved targets and passing evidence.
