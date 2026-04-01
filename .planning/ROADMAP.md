# ROADMAP — AI-Media-Factory

**Version:** v1
**Granularity:** Fine (9 phases)
**Execution:** Sequential — each phase builds on the previous
**Critical Path:** Script Gen → TTS → Subtitles → Remotion Composition → Export

---

## Phases

- [ ] **Phase 1: Project Foundation & Infrastructure** — FastAPI scaffolding, Celery+Redis queues, PostgreSQL+filesystem, dev environment
- [ ] **Phase 2: Configurable AI Model Architecture** — litellm gateway, provider-agnostic config, LM Studio/OpenAI/local model support
- [ ] **Phase 3: AI Script Generation** — User text input → AI generates structured video script
- [ ] **Phase 4: Text-to-Speech & Audio Timing** — edge-tts integration, voice synthesis, word-level timing extraction via SubMaker
- [x] **Phase 5: Subtitle Generation & Synchronization** — Auto-generate timed subtitle files from audio word boundaries (completed 2026-03-31)
- [ ] **Phase 6: Remotion Video Composition & Export** — React video composition, 1080p MP4 rendering, FFmpeg final encoding
- [ ] **Phase 7: Stock Media Auto-Matching** — Pexels API integration, script-driven keyword extraction, automatic image matching
- [ ] **Phase 8: Web Interface & REST API** — Single-page UI (input→progress→preview→download), REST endpoints for automation
- [ ] **Phase 9: Quality Assurance & Performance** — Generation time <5min, script quality, subtitle accuracy, user completion optimization

---

## Phase Details

### Phase 1: Project Foundation & Infrastructure
**Goal**: Developer can start the project and run async video generation tasks locally
**Depends on**: Nothing
**Requirements**: INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. Developer can start all services (API, Celery workers, Redis, PostgreSQL) with a single command
  2. Celery workers process test tasks on separate queues (tts/media/render/compose)
  3. PostgreSQL stores task metadata; filesystem stores media files; no files in database
  4. FFmpeg encodes a test video clip to 1080p MP4 via ffmpeg-python
**Plans**: 3 plans in 2 waves
- [ ] Plan 01: Project Scaffolding (pyproject.toml, FastAPI, docker-compose, Makefile)
- [ ] Plan 02: Celery + PostgreSQL + Storage (4 queues, models, filesystem)
- [ ] Plan 03: FFmpeg + Health Checks + Dev Bootstrap (ffmpeg-python, /api/health, tests)

### Phase 2: Configurable AI Model Architecture
**Goal**: System supports multiple LLM backends without code changes
**Depends on**: Phase 1
**Requirements**: CORE-06
**Success Criteria** (what must be TRUE):
  1. User can configure LLM provider via config file (LM Studio, OpenAI, local model)
  2. System abstracts model calls through litellm — switching providers requires zero code changes
  3. Both local models (LM Studio) and cloud APIs (OpenAI) produce valid completions
**Plans**: TBD

### Phase 3: AI Script Generation
**Goal**: User inputs a text topic and receives a structured video script ready for voice synthesis
**Depends on**: Phase 2
**Requirements**: CORE-01
**Success Criteria** (what must be TRUE):
  1. User enters a topic/description and receives a multi-paragraph narration script
  2. Generated script is structured with clear sections suitable for video scenes
  3. Script quality is usable without editing >80% of the time across diverse topics
**Plans**: TBD

### Phase 4: Text-to-Speech & Audio Timing
**Goal**: Script text is converted to natural-sounding voice narration with precise word timing data
**Depends on**: Phase 3
**Requirements**: CORE-02
**Success Criteria** (what must be TRUE):
  1. System generates voice audio from script text using edge-tts (default) or cloud TTS (fallback)
  2. Audio output includes word-level timing data (start time, duration per word) via SubMaker
  3. At least 5 Chinese and 3 English voices are available and selectable
  4. Both Chinese and English script content produce clear, natural-sounding narration
**Plans**: TBD

### Phase 5: Subtitle Generation & Synchronization
**Goal**: Timed subtitles are automatically generated from audio word boundaries and synced to playback
**Depends on**: Phase 4
**Requirements**: CORE-04
**Success Criteria** (what must be TRUE):
  1. System generates SRT/ASS subtitle files from TTS word-level timing data
  2. Subtitles display with correct text and timing during video preview
  3. Subtitle sync accuracy exceeds 95% when compared against audio playback
**Plans**: 3 plans in 3 waves
- [ ] Plan 01: Subtitle Model + Service (model, word grouping, SRT/ASS generation, sync validation)
- [ ] Plan 02: Celery Task + File Persistence (async subtitle task, storage integration)
- [ ] Plan 03: Test Suite (word grouping, format output, sync accuracy, edge cases)

### Phase 6: Remotion Video Composition & Export
**Goal**: All content (audio, subtitles, media) is composed into a downloadable 1080p video
**Depends on**: Phase 5
**Requirements**: CORE-03
**Success Criteria** (what must be TRUE):
  1. Remotion renders a video combining audio narration, timed subtitles, and background visuals
  2. Final output is a 1080p MP4 file downloadable by the user
  3. User can preview the composed video in the browser via @remotion/player before export
  4. FFmpeg final encoding produces a web-compatible MP4 (H.264, AAC)
**Plans**: 4 plans in 3 waves
- [ ] Plan 01: Remotion Project Scaffold + VideoComposition Component (remotion/, package.json, VideoComposition.tsx, Subtitles.tsx, parseSubtitles.ts)
- [ ] Plan 02: Server-Side Render Script (remotion/src/render.mjs — @remotion/renderer SSR)
- [ ] Plan 03: Preview Player + FastAPI Endpoint (remotion/player/, app/api/preview.py)
- [ ] Plan 04: Python Integration — ComposeService + Celery Task (Video model, compose_service.py, compose_tasks.py)

### Phase 7: Stock Media Auto-Matching
**Goal**: Video visuals are automatically enriched with relevant stock images matched to script content
**Depends on**: Phase 3 (needs script keywords)
**Requirements**: CORE-05
**Success Criteria** (what must be TRUE):
  1. System extracts keywords from each script section and searches Pexels API for matching images
  2. Downloaded images are integrated into the Remotion composition as background visuals
  3. At least 1 relevant image is matched per script section (>70% relevance)
**Plans**: 3 plans in 3 waves
- [x] Plan 01: Pexels Media Service (PexelsClient, KeywordExtractor, StockMediaService)
- [x] Plan 02: Media Matching Pipeline (ScriptMedia model, match_media_task Celery task)
- [x] Plan 03: Compose Integration + Tests (wire images into compose_video_task, test suite)

### Phase 8: Web Interface & REST API
**Goal**: Users can generate videos through a web UI or trigger generation via API
**Depends on**: Phase 6
**Requirements**: WEB-01, WEB-02
**Success Criteria** (what must be TRUE):
  1. User opens web app, enters text in a form, and submits a video generation request
  2. User sees real-time progress updates during generation (script → voice → subtitles → render)
  3. User can preview the generated video in-browser before downloading the MP4
  4. External systems can trigger video generation and poll status via REST API endpoints
**Plans**: 4 plans in 3 waves
- [ ] Plan 01: REST API + Orchestrator (video endpoints, OrchestratorService, status tracking)
- [ ] Plan 02: Web UI (HTML form, progress polling, video preview, download)
- [ ] Plan 03: Pipeline Task + Tests (end-to-end Celery task, API test suite, SSE streaming)
- [ ] Plan 04: Verification Checkpoint (human verification of full flow)
**UI hint**: yes

### Phase 9: Quality Assurance & Performance
**Goal**: End-to-end pipeline meets all quality targets for production readiness
**Depends on**: Phase 8
**Requirements**: QUAL-01, QUAL-02, QUAL-03, QUAL-04
**Success Criteria** (what must be TRUE):
  1. End-to-end video generation completes in under 5 minutes for a 1-3 minute video
  2. Generated scripts require no editing >80% of the time across a test set of topics
  3. Subtitle sync accuracy exceeds 95% in automated testing
  4. >60% of test users complete the full flow from input to download without abandoning
**Plans**: 5 plans in 2 waves
- [ ] Plan 01: Pipeline Benchmark Suite (timing instrumentation, benchmark runner, report generator)
- [ ] Plan 02: Script & Subtitle Quality Tests (script quality evaluator, sync accuracy test suite)
- [ ] Plan 03: UX Flow Instrumentation (completion tracking, UX test scenarios)
- [ ] Plan 04: Performance & Quality Optimization (pipeline tuning, prompt improvement, sync fixes)
- [ ] Plan 05: UX Polish & Completion Optimization (error recovery, download prominence, visual polish)

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Foundation & Infrastructure | 3/3 | ✅ Complete | 2026-03-30 |
| 2. Configurable AI Model Architecture | 3/3 | ✅ Complete | 2026-03-30 |
| 3. AI Script Generation | 2/2 | ✅ Complete | 2026-03-31 |
| 4. Text-to-Speech & Audio Timing | 2/2 | ✅ Complete | 2026-03-31 |
| 5. Subtitle Generation & Synchronization | 3/3 | ✅ Complete | 2026-03-31 |
| 6. Remotion Video Composition & Export | 4/4 | ✅ Complete | 2026-03-31 |
| 7. Stock Media Auto-Matching | 3/3 | ✅ Complete | 2026-04-01 |
| 8. Web Interface & REST API | 4/4 | ✅ Complete | 2026-04-01 |
| 9. Quality Assurance & Performance | 5/5 | ✅ Complete | 2026-04-01 |

---

## Dependency Graph

```
Phase 1 (Foundation)
  └─→ Phase 2 (AI Config)
        └─→ Phase 3 (Script Gen)
              ├─→ Phase 4 (TTS)
              │     └─→ Phase 5 (Subtitles)
              │           └─→ Phase 6 (Remotion) ─→ Phase 8 (Web UI) ─→ Phase 9 (QA)
              └─→ Phase 7 (Media Matching) ─────────────────────────┘
```

---

*Created: 2026-03-30 by GSD Roadmapper*
