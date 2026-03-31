---
phase: 06-remotion-composition-export
plan: 02
subsystem: remotion
tags: [remotion, render, ssr, mp4, h264]
dependency_graph:
  requires: [06-01]
  provides: [ssr-render-pipeline]
  affects: [06-04]
tech_stack:
  added: []
  patterns: ["@remotion/bundler + selectComposition + renderMedia SSR pipeline", "CLI arg parsing (ESM .mjs)"]
key_files:
  created:
    - remotion/src/render.mjs
  modified: []
decisions:
  - ESM (.mjs) format for Remotion bundler compatibility
  - CRF 18 for high quality, preset fast for speed
  - 50% CPU concurrency default (os.cpus().length / 2)
  - Temp JSON file for props (avoids shell escaping issues)
metrics:
  duration: "5m"
  completed: "2026-03-31"
  tasks_completed: 1
  files_created: 1
---

# Phase 06 Plan 02: SSR Render Script Summary

## One-liner
Node.js ESM render script that bundles Remotion project, selects VideoComposition, and renders to 1080p H.264 MP4 via @remotion/renderer SSR APIs.

## What Was Built

### Render Script (`remotion/src/render.mjs`)
- **CLI args:** `--props <json-file>`, `--output <path>`, `--concurrency <n>`
- **Pipeline:** `bundle()` → `selectComposition()` → `renderMedia()` → MP4 output
- **Encoding:** H.264 codec, CRF 18, preset fast, AAC audio (Remotion defaults)
- **Path resolution:** Resolves relative audio/image paths against project root
- **Progress:** Prints percentage to stdout via `onProgress` callback
- **Error handling:** Catches all errors, prints to stderr, exits with code 1

## Deviations from Plan
None — plan executed exactly as written.

## Verification Results
- Module loads: **PASSED** (`node -e "import('./src/render.mjs')"`)
- Full render test: **SKIPPED** (requires Chrome headless shell download, first run only)

## Known Stubs
None.
