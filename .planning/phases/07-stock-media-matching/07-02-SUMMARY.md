---
phase: 07-stock-media-matching
plan: 02
subsystem: media-pipeline
tags: [celery, sqlalchemy, async, media-matching]
dependency_graph:
  requires:
    - Plan 07-01 (media_service.py)
    - app/models/script.py (FK target)
    - app/celery_app.py (media queue routing)
  provides:
    - ScriptMedia model (status tracking + JSONB results)
    - match_media_task (async Celery task)
  affects:
    - Plan 07-03 (compose integration reads ScriptMedia)
tech_stack:
  added:
    - ScriptMedia SQLAlchemy model with JSONB matched_images
  patterns:
    - sync wrapper → asyncio.run → async DB ops (matches compose_tasks pattern)
    - Status lifecycle: pending → matching → completed | failed
    - Graceful error handling: PexelsClientError → status=failed + error message
key_files:
  created:
    - app/models/script_media.py
    - app/tasks/media_tasks.py
  modified:
    - app/models/__init__.py (added ScriptMedia export)
decisions: []
---

# Phase 7 Plan 02: Media Matching Pipeline Summary

## One-liner
ScriptMedia model for tracking media match status and Celery task for async keyword→Pexels→download execution.

## What Was Built

### ScriptMedia Model
- Table: `script_media`
- Fields: id (UUID PK), script_id (FK → scripts), celery_task_id, matched_images (JSONB), status, error, timestamps
- JSONB `matched_images` format: `[{"section_index": 0, "image_paths": [...], "keywords": [...]}]`
- Status lifecycle: `pending` → `matching` → `completed` | `failed`

### match_media_task Celery Task
- Task name: `app.tasks.media.match` (routes to "media" queue)
- `acks_late=True` for reliability
- Reads PEXELS_API_KEY from environment
- Parses script.content as JSON → extracts sections array
- Creates ScriptMedia record → runs StockMediaService → updates with results
- Error handling mirrors compose_tasks pattern (try/except → status=failed → flush)

## Verification
- ✅ `ScriptMedia.__tablename__ == "script_media"`
- ✅ `match_media_task.name == "app.tasks.media.match"`
- ✅ Full import chain verified

## Deviations from Plan
None — plan executed exactly as written.

## Self-Check: PASSED
