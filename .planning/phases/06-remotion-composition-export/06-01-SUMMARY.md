---
phase: 06-remotion-composition-export
plan: 01
subsystem: remotion
tags: [remotion, video, composition, react, srt-parser]
dependency_graph:
  requires: [CORE-03]
  provides: [remotion-scaffold, video-composition, subtitle-parser]
  affects: [06-02, 06-03, 06-04]
tech_stack:
  added: ["@remotion/cli@4.0.441", "@remotion/renderer@4.0.441", "@remotion/bundler@4.0.441", "@remotion/player@4.0.441", "@remotion/media@4.0.441", "mediabunny@1.40.1", "react@19", "typescript@5"]
  patterns: ["Remotion Composition + calculateMetadata", "SRT-to-frame conversion", "CSS-in-JS subtitle overlay"]
key_files:
  created:
    - remotion/package.json
    - remotion/tsconfig.json
    - remotion/src/parseSubtitles.ts
    - remotion/src/parseSubtitles.test.ts
    - remotion/src/Subtitles.tsx
    - remotion/src/VideoComposition.tsx
    - remotion/src/index.ts
  modified: []
decisions:
  - mediabunny for audio duration detection (per Remotion docs recommendation)
  - calculateMetadata for dynamic durationInFrames from audio length
  - 30-frame buffer after last subtitle for clean ending
  - CSS-in-JS inline styles only (no external CSS files)
metrics:
  duration: "15m"
  completed: "2026-03-31"
  tasks_completed: 4
  files_created: 8
  tests_passed: 17
---

# Phase 06 Plan 01: Remotion Project Scaffold Summary

## One-liner
Remotion project with parametrizable VideoComposition combining audio, timed subtitles, and background visuals into a 1080p video composition.

## What Was Built

### Remotion Project (`remotion/`)
- **package.json** — Node.js project with Remotion 4.0.441 dependencies (cli, renderer, bundler, player, media) + mediabunny for audio duration detection
- **tsconfig.json** — ES2022 target, react-jsx, bundler module resolution, strict mode

### SRT Parser (`remotion/src/parseSubtitles.ts`)
- `parseSrt(srtText, fps)` → `SubtitleSegment[]`
- Converts `HH:MM:SS,mmm` timestamps to milliseconds and frame numbers
- Handles multi-line text (joins with space), empty/invalid input
- 17 unit tests passing

### Subtitles Component (`remotion/src/Subtitles.tsx`)
- Renders active subtitle at bottom 80% vertical position
- White text on semi-transparent black pill background (48px, text-shadow)
- Fade in/out over 5 frames near segment boundaries via `interpolate()`

### VideoComposition (`remotion/src/VideoComposition.tsx`)
- **Layers:** Background (gradient or timed crossfade images) → Audio → Title overlay → Subtitles
- **calculateMetadata:** Uses mediabunny `Input.computeDuration()` for dynamic `durationInFrames`
- **Props:** `audioSrc`, `subtitleText`, `backgroundImages[]`, `titleText?`, `fps?`, `width?`, `height?`
- **RemotionRoot:** Registers `<Composition id="VideoComposition">` with defaults

### Remotion Root (`remotion/src/index.ts`)
- `registerRoot(RemotionRoot)` — entry point for Remotion CLI

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] mediabunny API change**
- **Found during:** Task 4 (VideoComposition)
- **Issue:** mediabunny API uses `new Input({ source: new UrlSource(url), formats: ALL_FORMATS })` — not the simpler `{ source: { url } }` pattern assumed in the plan
- **Fix:** Updated calculateMetadata to use `UrlSource` constructor + `ALL_FORMATS` array, and `input.computeDuration()` as instance method (not standalone)
- **Files modified:** `remotion/src/VideoComposition.tsx`

## Verification Results
- TypeScript compilation: **PASSED** (`npx tsc --noEmit` — no errors)
- SRT parser tests: **17/17 PASSED**
- Remotion bundle: **SUCCESS** (bundled in 2474ms, composition registered)
- Package resolution: **ALL OK** (@remotion/cli, renderer, bundler, media, mediabunny)

## Known Stubs
None — all components are fully implemented.
