---
phase: 04-text-to-speech-audio-timing
plan: 01
subsystem: tts
tags: [dependencies, model, voice-registry, foundation]
dependency_graph:
  requires: [app/db.py, app/models/project.py]
  provides: [edge-tts, srt, AudioFile, VoiceManagerService]
  affects: [04-02]
tech_stack:
  added: [edge-tts>=7.0, srt>=5.0]
  patterns: [SQLAlchemy JSONB, module singleton]
key_files:
  created: [app/models/audio.py, app/services/voice_manager.py]
  modified: [pyproject.toml]
decisions:
  - "Curated 5 ZH + 3 EN voices (XiaoxiaoNeural default ZH, AriaNeural default EN)"
  - "AudioFile.word_timing as JSONB for flexible per-word timing storage"
metrics:
  completed: "2026-03-31"
  tasks: 3/3
---

# Phase 4 Plan 01: TTS Foundation — Dependencies, Audio Model, Voice Registry Summary

## One-liner

edge-tts and srt dependencies added; AudioFile SQLAlchemy model with word_timing JSONB; VoiceManagerService with 5 Chinese + 3 English curated voices.

## What Was Built

### 1. Dependencies (pyproject.toml)
- Added `edge-tts>=7.0` — Microsoft Edge free TTS engine (async Python SDK)
- Added `srt>=5.0` — SRT subtitle format library (required by SubMaker)

### 2. AudioFile Model (app/models/audio.py)
SQLAlchemy model for audio metadata persistence:
- `script_id` FK → scripts.id (links audio to source script)
- `voice`, `language` — voice name and language code
- `file_path` — relative path in storage
- `word_timing` (JSONB) — per-word timing data for subtitle sync
- `status`, `error`, `created_at`, `updated_at`, `completed_at` — lifecycle tracking
- Follows exact pattern from app/models/project.py and app/models/script.py

### 3. VoiceManagerService (app/services/voice_manager.py)
Voice registry and selection service:
- **5 Chinese voices:** XiaoxiaoNeural (default), YunxiNeural, YunjianNeural, XiaoyiNeural, YunyangNeural
- **3 English voices:** AriaNeural (default), GuyNeural, JennyNeural
- `list_voices(language, gender)` — filtered voice listing
- `get_default_voice(language)` — default voice per language
- `get_voice(name)` — exact voice lookup
- `discover_voices(language)` — async edge-tts VoicesManager discovery with fallback

## Verification Results

| Check | Status |
|-------|--------|
| pyproject.toml contains edge-tts | ✅ |
| pyproject.toml contains srt | ✅ |
| AudioFile imports | ✅ |
| VoiceManagerService imports | ✅ |
| ZH voice count >= 5 | ✅ (5) |
| EN voice count >= 3 | ✅ (3) |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

All artifacts created, imports verified, voice counts confirmed.
