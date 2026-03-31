---
phase: 06-remotion-composition-export
plan: 03
subsystem: [remotion, api]
tags: [preview, player, fastapi, react]
dependency_graph:
  requires: [06-01]
  provides: [preview-player, preview-api]
  affects: []
tech_stack:
  added: []
  patterns: ["@remotion/player embedding", "URL query param props", "FastAPI StaticFiles mount"]
key_files:
  created:
    - remotion/player/index.html
    - remotion/player/index.tsx
    - remotion/player/App.tsx
    - app/api/preview.py
  modified:
    - app/main.py
decisions:
  - Preview player reads props from URL query params (no build step needed)
  - StaticFiles mount for media assets (audio, images) from storage/assets/
  - /preview/data/{audio_id} endpoint constructs props from DB models
metrics:
  duration: "5m"
  completed: "2026-03-31"
  tasks_completed: 2
  files_created: 4
  files_modified: 1
---

# Phase 06 Plan 03: Preview Player Summary

## One-liner
In-browser preview player using @remotion/player with playback controls, served via FastAPI /preview/ endpoint with auto-loading composition data from the database.

## What Was Built

### Preview Player (`remotion/player/`)
- **index.html** — HTML5 boilerplate with dark background, module script entry
- **index.tsx** — React root rendering App component
- **App.tsx** — Embeds `@remotion/player` with VideoComposition
  - Reads props from URL query: `?audio=`, `?subtitles=`, `?images=`, `&title=`
  - Calculates duration from subtitle segments + 3-second buffer
  - 1920×1080 composition, 30fps, playback controls enabled
  - Responsive layout (max-width 960px, 16:9 aspect ratio)

### FastAPI Preview Endpoint (`app/api/preview.py`)
- `GET /preview/` — Serves player HTML
- `GET /preview/data/{audio_id}` — Returns composition props JSON from DB
  - Loads AudioFile + latest SRT Subtitle
  - Constructs audio URL, subtitle content, image URLs
- Static mounts: `/preview/assets` (player JS), `/preview/media` (storage/assets)

### main.py Update
- Added `preview_router` import and `app.include_router(preview_router)`

## Deviations from Plan
None — plan executed exactly as written.

## Verification Results
- Preview router import: **PASSED**
- main.py integration: **PASSED** (`from app.main import app`)
- Player files: **ALL PRESENT** (index.html, index.tsx, App.tsx)

## Known Stubs
None.
