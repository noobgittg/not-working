# MMW-BOT-PRO — Production Fix Report

## Critical errors fixed

### 1. MongoDB `E11000 duplicate key` / concurrent `/start`
- Replaced `find_one()` + `insert_one()` user creation with atomic `find_one_and_update(..., upsert=True)`.
- Applied the same atomic pattern to chat creation.
- Removed all `$set` / `$setOnInsert` field collisions that MongoDB rejects as conflicting update paths.
- Fixed caption insertion so `$addToSet` does not collide with `$setOnInsert`.
- Kept the existing unique indexes for `user_id`, `chat_id`, and `file_id`.

Files:
- `app/database/repositories/user_repo.py`
- `app/database/repositories/chat_repo.py`
- `app/database/repositories/file_repo.py`
- `app/database/mongodb.py`

### 2. Telegram `BUTTON_URL_INVALID`
- Added central HTTP(S)-only Telegram inline-button validation.
- Removed custom `intent:`, `playit://`, and `kmplayer://` button URLs.
- Web/stream/download buttons are generated only when the URL is Telegram-valid.
- Stream download buttons now use the direct `/file/{file_id}` endpoint.

Files:
- `app/utils/helpers.py`
- `app/bot/handlers/streamer.py`
- `app/bot/handlers/start.py`
- `app/bot/handlers/callbacks.py`
- `app/bot/handlers/extra.py`
- `app/web/routes/pages.py`
- `app/web/routes/api.py`
- `app/web/templates/dl.html`
- `app/web/templates/watch.html`

### 3. Rename >2 GB handling
- Added an early source-size check.
- Added a second post-download size check so an unexpected size mismatch is still rejected.
- User-facing message explicitly says files over 2 GB cannot be renamed.
- Rename preserves the original extension unless a new valid extension is explicitly supplied.

File:
- `app/bot/handlers/rename.py`

### 4. FFmpeg compressor / MediaInfo
- Rebuilt `get_media_attributes()` to return one stable dictionary contract.
- Fixed the previous tuple-vs-dictionary mismatch used by rename/compressor.
- Compressor now auto-detects video vs audio streams.
- Video output: H.264/AAC MP4 with even dimensions and broad playback compatibility.
- Audio-only output: AAC/M4A.
- FFmpeg progress is throttled to avoid Telegram edit flooding.
- FFmpeg failures are logged with a bounded stderr tail instead of producing noisy unhandled traces.
- Oversized compressor output is split into safe binary parts before Telegram upload.
- Unsupported non-media documents return a clear message instead of an opaque FFmpeg failure.

Files:
- `app/services/ffmpeg_service.py`
- `app/bot/handlers/compressor.py`
- `app/bot/handlers/extra.py`

### 5. Deep MediaInfo / rename workflow stability
- MediaInfo temp files now live under the configured download directory.
- Incoming filenames used for temporary paths are sanitized.
- Temporary directories are removed on both success and failure.
- Rename workflow cleanup is deterministic.
- Thumbnail path/workdir argument mismatch was corrected.

Files:
- `app/bot/handlers/extra.py`
- `app/bot/handlers/rename.py`
- `app/services/thumb_service.py`

### 6. Streaming/file delivery
- Added/retained `/stream/{file_id}` with HTTP 206 range handling.
- Supports normal ranges, open-ended ranges, and suffix ranges.
- Corrects the initial partial-chunk offset by trimming the first streamed chunk.
- Added `/file/{file_id}` as a direct attachment/download stream.
- Added `HEAD /stream/{file_id}`.
- Added proper `Content-Range`, `Content-Length`, `Accept-Ranges`, and content disposition headers.
- File URLs are indexed against the actual Telegram message reference stored in MongoDB.

Files:
- `app/web/routes/stream.py`
- `app/bot/handlers/streamer.py`

### 7. Auto-delete reliability
- Telegram deletion batches are capped conservatively.
- Expired DB tasks are removed only after successful Telegram deletion.
- Failed deletions remain queued for a later retry.

Files:
- `app/services/autodel_service.py`
- `app/database/repositories/chat_repo.py`

### 8. Cancellation / concurrency
- Added per-user active operation tracking.
- Prevents overlapping rename/compress operations for the same user.
- Added global concurrent-task limiting.
- `/cancel` and callback cancellation now cancel the active operation task.

Files:
- `app/utils/task_manager.py`
- `app/bot/handlers/cancel.py`
- `app/bot/handlers/rename.py`
- `app/bot/handlers/compressor.py`

### 9. Thumbnail safety
- Custom/remote thumbnail URLs are limited to public HTTP(S) targets.
- Private/loopback/reserved targets are rejected.
- Image downloads are size-limited and content-type checked.
- Redirect handling is constrained.

File:
- `app/services/thumb_service.py`

### 10. Configuration / deployment
- Centralized `.env` loading and startup validation.
- Removed unused dependencies and pinned core production versions.
- Python runtime moved to 3.12.
- Docker image includes FFmpeg/ffprobe.
- Docker Compose now waits for MongoDB health and does not publish MongoDB to the host.
- Optional `THAM_URL` is empty by default to avoid an external fallback request on every file.
- CORS credentials are disabled for wildcard origins.

Files:
- `config.py`
- `.env.example`
- `requirements.txt`
- `runtime.txt`
- `Dockerfile`
- `docker-compose.yml`
- `entrypoint.sh`
- `Procfile`
- `koyeb.yaml`
- `main.py`

## Validation performed

- Python source compile: passed for the repository.
- Local import-path audit: passed; no missing local `app.*` modules.
- Mongo update-shape regression test: passed; no `$set`/`$setOnInsert` conflicts in tested repository update paths.
- FFmpeg smoke test: passed for generated video and audio samples.
- MediaInfo smoke test: passed for video/audio stream detection and dimensions.
- Compression smoke test: passed for video and audio outputs.
- File splitting smoke test: passed.
- Range parsing smoke test: passed for bounded, open-ended, suffix, and clamped ranges.
- Per-user concurrency/cancellation guard smoke test: passed.
- Jinja template smoke test: passed for HTML templates.
- Shell syntax check: passed for `entrypoint.sh`.
- FFmpeg/ffprobe were available in the audit environment.

A full live Telegram + MongoDB integration run could not be executed in this isolated environment because external package-index/DNS access was unavailable; the repository therefore was validated with static compilation, source audits, mocked database update behavior, template checks, and real local FFmpeg execution rather than claiming a live deployment test.
