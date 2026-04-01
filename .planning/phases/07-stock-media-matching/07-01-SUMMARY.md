---
phase: 07-stock-media-matching
plan: 01
subsystem: media-service
tags: [pexels, stock-media, keyword-extraction, httpx]
dependency_graph:
  requires:
    - Phase 3 (script sections format)
    - app/storage.py (StorageService)
    - httpx (HTTP client)
  provides:
    - PexelsClient (search + download)
    - KeywordExtractor (English/Chinese)
    - StockMediaService (orchestration)
  affects:
    - Plan 07-02 (depends on media_service.py)
    - Plan 07-03 (depends on media_service.py)
tech_stack:
  added:
    - Pexels REST API integration via raw httpx
  patterns:
    - Context manager pattern for HTTP client lifecycle
    - Stop-word filtering without NLP dependencies
    - Chinese text support via regex CJK detection
key_files:
  created:
    - app/services/media_service.py
  modified:
    - app/config.py (added pexels_api_key)
    - .env.example (added PEXELS_API_KEY)
decisions: []
---

# Phase 7 Plan 01: Pexels Media Service Summary

## One-liner
Pexels API client with English/Chinese keyword extraction for script-driven stock image search and download.

## What Was Built

### PexelsClient
- `search_photos(query, per_page, orientation)` — GET /v1/search with auth header
- `download_photo(url, save_path)` — stream-download to local path
- `search_and_download(query, save_dir)` — convenience: search + download top results
- Context manager support (`with PexelsClient(...) as client:`)
- Error handling: 429 rate limit, timeout, HTTP errors → PexelsClientError

### KeywordExtractor
- `extract_keywords(section)` — 1-5 keywords from heading + content
- English: tokenize, lowercase, filter stop words, keep words ≥ 3 chars
- Chinese: split by CJK punctuation, preserve meaningful segments > 1 char
- Short content (< 3 meaningful words) → heading-only fallback
- Deduplication while preserving order
- `build_search_query(keywords)` — space-join, max 100 chars

### StockMediaService
- `match_images_to_script(script_sections, save_dir)` — per-section keyword→search→download
- Continues on per-section failure (doesn't abort entire script)
- Renames files with section index for ordering

## Verification
- ✅ All classes importable from `app.services.media_service`
- ✅ KeywordExtractor tested with English, Chinese, empty content, short content
- ✅ No new pip dependencies (uses existing httpx)

## Deviations from Plan
None — plan executed exactly as written.

## Self-Check: PASSED
