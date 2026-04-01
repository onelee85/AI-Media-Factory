---
phase: 09-quality-assurance-performance
plan: "03"
subsystem: web-ui
tags: [UX, tracking, completion-rate, QUAL-04]
dependency_graph:
  requires: [app/web/app.js, app/api/videos.py]
  provides: [flowTracker, debug panel, UX completion tests]
  affects: [09-05]
tech_stack:
  added: []
  patterns: [flowTracker object, window exposure, debug panel]
key_files:
  created:
    - tests/test_ux_completion.py
  modified:
    - app/web/app.js
    - app/web/index.html
decisions: []
metrics:
  duration: ~5 minutes
  completed: 2026-04-01
  files_changed: 3
  lines_added: 315
  tests_added: 15
---

# Phase 9 Plan 03: Web UI Completion Tracking + UX Tests Summary

## What Was Built

Client-side completion tracking and UX test suite for measuring QUAL-04 (>60% completion rate).

**Key changes:**
- Added `flowTracker` object in `app/web/app.js`:
  - Tracks 5 steps: input, submit, progress, preview, download
  - `mark(step)` records step completion, prevents duplicate marks
  - `completionSummary()` returns {completed, total, rate, steps}
  - `getDropOff()` identifies incomplete steps
  - `getElapsed()` tracks time since first step
  - `_updateDebugPanel()` live-updates debug overlay
  - Exposed on `window.flowTracker` for test/debug access
- Added hidden debug panel in `index.html` (visible with `?debug=1` query param)
- Created `tests/test_ux_completion.py` with 15 tests:
  - API flow tracking: all required endpoints exist
  - Completion rate calculation: (downloaded / total) * 100
  - Drop-off identification per step
  - User journey scenarios: happy path, abandon at progress, abandon at submit
  - 70% > 60% target passes, 50% < 60% target fails

## Files Created

| File | Purpose | Lines | Tests |
|------|---------|-------|-------|
| tests/test_ux_completion.py | UX completion test suite | ~256 | 15 |

## Files Modified

| File | Change |
|------|--------|
| app/web/app.js | Added flowTracker object, mark() calls at each flow step |
| app/web/index.html | Added hidden debug panel with ?debug=1 toggle |

## Verification

- [x] `grep -c "flowTracker" app/web/app.js` — tracking code present
- [x] `python -m pytest tests/test_ux_completion.py -v` — 15 passed
- [x] `python -m pytest tests/ -v` — 149 passed, 6 skipped (no regressions)

## Checkpoint: Human Verification

**What built:** Web UI completion tracking (flowTracker) + UX test suite
**How to verify:**
1. Start the web server: `make run` or `uvicorn app.main:app --reload`
2. Open http://localhost:8000/web/?debug=1
3. Enter text in the form → verify "input" step lights up in debug panel
4. Click generate → verify "submit" step lights up
5. Observe progress → verify "progress" step lights up
6. If video completes → verify "preview" and "download" steps
7. Run tests: `python -m pytest tests/test_ux_completion.py -v`

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
