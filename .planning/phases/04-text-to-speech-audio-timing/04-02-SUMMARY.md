---
phase: 04-text-to-speech-audio-timing
plan: 02
subsystem: tts
tags: [tts, edge-tts, audio-synthesis, word-timing, srt]
dependency_graph:
  requires: [04-01, app/config.py, app/services/voice_manager.py]
  provides: [TTSService, generate_tts, TTSServiceError]
  affects: [05-subtitles, 06-remotion]
tech_stack:
  used: [edge_tts.Communicate, edge_tts.SubMaker]
  patterns: [async streaming, module-level convenience function]
key_files:
  created: [app/services/tts_service.py]
decisions:
  - "Streaming capture via communicate.stream() (not save()) to capture both audio and WordBoundary events"
  - "Word timing in seconds + raw 100ns units for flexibility"
  - "Error cleanup: delete partial audio file on failure"
  - "Voice validation before TTS call to avoid edge-tts cryptic errors"
metrics:
  completed: "2026-03-31"
  tasks: 1/1
---

# Phase 4 Plan 02: Core TTS Service Summary

## One-liner

TTSService using edge-tts Communicate for MP3 synthesis with SubMaker word-level timing extraction, SRT generation, and multi-section batch processing.

## What Was Built

### TTSService (app/services/tts_service.py)

Core TTS service with three main capabilities:

#### `generate()` — Single text → audio + timing
- Accepts text, voice, language, rate/volume/pitch parameters
- Uses `edge_tts.Communicate` for async streaming synthesis
- Captures `WordBoundary` events via `SubMaker.feed()`
- Returns dict with: `audio_path`, `voice`, `language`, `duration_seconds`, `word_timing`, `srt_content`
- Word timing structure: `[{word, start, end, offset, duration}]` — seconds + raw 100ns units
- Auto-generates output path in `storage_root/tts/{uuid}.mp3` if not specified
- Cleans up partial file on error

#### `generate_from_script_sections()` — Multi-section batch
- Processes list of script sections (from Phase 3 output)
- Each section → separate MP3 file with heading-based filename
- Sequential processing for reliability

#### `get_supported_voices()` — Voice listing
- Delegates to VoiceManagerService for filtered voice list

#### Module exports
- `TTSService` class
- `TTSServiceError` exception
- `generate_tts()` async convenience function

## Verification Results

| Check | Status |
|-------|--------|
| tts_service.py exists | ✅ |
| Imports edge_tts.Communicate | ✅ |
| Imports edge_tts.SubMaker | ✅ |
| Imports voice_manager_service | ✅ |
| TTSService class present | ✅ |
| generate() method present | ✅ |
| generate_from_script_sections() present | ✅ |
| TTSServiceError exported | ✅ |
| generate_tts() exported | ✅ |
| Module imports successfully | ✅ |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

All artifacts created, imports verified, API surface confirmed.
