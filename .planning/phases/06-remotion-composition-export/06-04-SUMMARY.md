---
phase: 06-remotion-composition-export
plan: 04
subsystem: [backend, celery]
tags: [video-model, compose-service, celery-task, subprocess]
dependency_graph:
  requires: [06-01, 06-02]
  provides: [video-model, compose-service, compose-task]
  affects: []
tech_stack:
  added: []
  patterns: ["SQLAlchemy model (UUID PK, status lifecycle, JSONB)", "sync wrapper → asyncio.run → async DB ops", "subprocess.run for Node.js invocation"]
key_files:
  created:
    - app/models/video.py
    - app/services/compose_service.py
    - app/tasks/compose_tasks.py
  modified:
    - app/models/__init__.py
    - app/storage.py
decisions:
  - Video model follows exact subtitle.py pattern (UUID PK, FK to scripts/audio, status lifecycle)
  - ComposeService uses tempfile for props JSON (avoids shell injection)
  - compose_video_task on "compose" queue (matches celery_app.py task_routes)
  - Auto-find latest SRT subtitle if subtitle_id not provided
  - 600s subprocess timeout matches Celery task_time_limit
metrics:
  duration: "10m"
  completed: "2026-03-31"
  tasks_completed: 4
  files_created: 3
  files_modified: 2
---

# Phase 06 Plan 04: Python Integration Summary

## One-liner
Video SQLAlchemy model with render status lifecycle, ComposeService for subprocess-based Remotion invocation, and Celery compose_video_task for async rendering — complete Python→Node.js bridge.

## What Was Built

### Video Model (`app/models/video.py`)
- `videos` table with: id (UUID PK), script_id (FK), audio_id (FK), subtitle_id (FK), celery_task_id, file_path, file_size_bytes, duration_seconds, width (1920), height (1080), codec (h264), render_props (JSONB), status (pending→rendering→completed/failed), error, created_at, updated_at, completed_at

### ComposeService (`app/services/compose_service.py`)
- `build_render_props(audio_path, subtitle_content, title, images)` → props dict
- `render(props, output_path)` → subprocess `node render.mjs --props ... --output ...`
- `compose(audio_file_path, subtitle_content, output_path, ...)` → validate → build → render
- Uses tempfile for props JSON, 600s timeout, captures stdout/stderr

### Celery Task (`app/tasks/compose_tasks.py`)
- `compose_video_task(audio_id, subtitle_id?, title?)` — registered as `app.tasks.compose.video`
- Routed to `compose` queue (from celery_app.py)
- Async core follows subtitle_tasks.py pattern: load audio → find subtitle → create Video record → ComposeService.compose() → update status
- Error handling: catches ComposeServiceError and general exceptions, sets Video.status=failed

### StorageService Update (`app/storage.py`)
- Added `video_props_dir(job_id)` for temp render props storage

### models/__init__.py
- Added `Video` to imports and `__all__`

## Deviations from Plan
None — plan executed exactly as written.

## Verification Results
- Video model import: **PASSED** (table: videos)
- ComposeService import: **PASSED**
- compose_video_task import: **PASSED** (name: app.tasks.compose.video)
- Full import chain: **ALL OK**
- StorageService.render_dir: **EXISTS** (pre-existing)
- StorageService.video_props_dir: **ADDED**

## Known Stubs
None — all components are fully implemented and importable.
