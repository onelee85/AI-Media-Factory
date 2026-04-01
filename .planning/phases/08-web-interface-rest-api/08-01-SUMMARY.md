---
phase: 08-web-interface-rest-api
plan: "01"
subsystem: web-api
tags: [rest-api, orchestrator, celery, fastapi]
dependency_graph:
  requires:
    - app/models/video.py (Video model)
    - app/models/script.py (Script model)
    - app/models/audio.py (AudioFile model)
    - app/models/subtitle.py (Subtitle model)
    - app/models/project.py (Project model)
    - app/tasks/script_tasks.py (generate_script_task)
    - app/tasks/compose_tasks.py (compose_video_task)
    - app/services/compose_service.py (ComposeService)
    - app/services/tts_service.py (TTSService)
    - app/services/subtitle_service.py (SubtitleService)
    - app/services/script_generator.py (ScriptGeneratorService)
  provides:
    - REST API for video generation lifecycle (6 endpoints)
    - OrchestratorService for pipeline management
    - Video pipeline Celery task
    - TTS Celery task wrapper
  affects:
    - app/main.py (router registration, web mount)
    - app/celery_app.py (pipeline task routing)
tech_stack:
  added:
    - FastAPI APIRouter for video endpoints
    - SSE streaming via StreamingResponse
    - OrchestratorService async singleton
  patterns:
    - Pydantic request/response models (matching scripts.py pattern)
    - get_db dependency injection for DB sessions
    - Video.render_props for pipeline stage tracking
    - _resolve_stage() fallback resolution chain
key_files:
  created:
    - app/api/videos.py
    - app/services/orchestrator.py
    - app/tasks/video_pipeline.py
    - app/tasks/tts_tasks.py
  modified:
    - app/main.py
    - app/celery_app.py
decisions:
  - "Single pipeline task (not Celery chain): Simpler debugging, reliable stage tracking via render_props"
  - "TTS task wrapper created: Plan required standalone TTS Celery entry point that didn't exist"
  - "SSE endpoint added in Wave 1: Needed for real-time streaming, included early for completeness"
  - "Pre-created DB records: Orchestrator creates Project/Script/Audio/Subtitle/Video upfront for tracking"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-01"
  tasks_completed: 3/3
  files_created: 4
  files_modified: 2
  lines_added: ~1042
---

# Phase 8 Plan 01: REST API & OrchestratorService Summary

## One-Liner

Video generation REST API with 6 endpoints (generate, get, status, download, list, SSE stream) backed by OrchestratorService that creates DB records and dispatches a full-pipeline Celery task.

## What Was Built

### 1. OrchestratorService (`app/services/orchestrator.py`)
- `start_pipeline(prompt, title, voice)` → creates Project, Script, AudioFile, Subtitle, Video records → dispatches `generate_video_pipeline_task` → returns `{video_id, celery_task_id, status}`
- `get_video_with_details(video_id)` → returns Video with nested script/audio/subtitle status
- Module-level singleton `orchestrator_service`

### 2. Video REST API (`app/api/videos.py`)
| Endpoint | Description |
|----------|-------------|
| `POST /api/videos/generate` | Start pipeline, returns 201 with video_id |
| `GET /api/videos/{id}` | Full video details with related records |
| `GET /api/videos/{id}/status` | Lightweight status with pipeline stage |
| `GET /api/videos/{id}/download` | FileResponse for MP4 |
| `GET /api/videos` | List videos with status filter, pagination |
| `GET /api/videos/{id}/stream` | SSE streaming for real-time updates |

### 3. Pipeline Celery Task (`app/tasks/video_pipeline.py`)
- `generate_video_pipeline_task` — runs all 5 stages sequentially within one task
- Stage tracking via `Video.render_props.stage`
- Stages: script → audio → subtitles → media → compose
- Graceful degradation: media matching is optional (Pexels API may not be configured)

### 4. TTS Celery Task (`app/tasks/tts_tasks.py`)
- `generate_audio_task` — wraps TTSService as standalone Celery task
- Creates AudioFile record with word_timing data

### 5. Supporting Changes
- `app/main.py`: Registered videos_router, added web UI mount point
- `app/celery_app.py`: Added `app.tasks.pipeline.*` → scripts queue routing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] TTS Celery task didn't exist**
- **Found during:** Task 1 (OrchestratorService)
- **Issue:** Orchestrator needed a TTS Celery task but only `tts_test_task` existed
- **Fix:** Created `app/tasks/tts_tasks.py` with `generate_audio_task` wrapper
- **Files modified:** app/tasks/tts_tasks.py (new)
- **Commit:** 87840f3

**2. [Rule 3 - Blocking] Pipeline task needed before orchestrator**
- **Found during:** Task 1 (OrchestratorService)
- **Issue:** Orchestrator imports `generate_video_pipeline_task` which was planned for 08-03
- **Fix:** Created pipeline task in 08-01 (needed by orchestrator), 08-03 enhanced with tests
- **Files modified:** app/tasks/video_pipeline.py (new)
- **Commit:** 87840f3

**3. [Rule 1 - Lint] Unused imports in multiple files**
- **Found during:** Post-creation lint check
- **Fix:** Auto-fixed with `ruff --fix` (6 errors), manual fix for unused variable
- **Commit:** 87840f3

## Verification Results

- ✅ `python -c "from app.services.orchestrator import OrchestratorService"` — OK
- ✅ `python -c "from app.api.videos import videos_router"` — prefix: /api/videos
- ✅ `python -c "from app.tasks.video_pipeline import generate_video_pipeline_task"` — OK
- ✅ `python -c "from app.tasks.tts_tasks import generate_audio_task"` — OK
- ✅ `ruff check` — all checks passed
- ✅ All 6 video endpoints registered in app.routes
- ✅ SSE streaming endpoint registered

## Known Stubs

None — all endpoints are fully implemented. Media matching degrades gracefully when Pexels API is not configured.

## Self-Check: PASSED

- ✅ app/api/videos.py exists (425 lines)
- ✅ app/services/orchestrator.py exists (197 lines)
- ✅ app/tasks/video_pipeline.py exists (338 lines)
- ✅ app/tasks/tts_tasks.py exists (131 lines)
- ✅ Commit 87840f3 exists
- ✅ All 6 endpoints registered in app routes
