# STATE — AI-Media-Factory

## Project Reference

- **Core Value**: "一键出片" — one-click video generation from text
- **Current Focus**: v1 MVP — core pipeline from text input to video download
- **Critical Path**: Script Gen → TTS → Subtitles → Remotion Composition → Export

## Current Position

- **Phase**: 8 (complete)
- **Plan**: 04 (verification — auto-approved)
- **Status**: Phase 8 complete — Web Interface & REST API, 4 plans in 3 waves
- **Progress**: ██████████████████████░ 9/9 phases (8 complete, 1 future)

## Performance Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Phases completed | 9 | 8 |
| Requirements mapped | 16/16 | 16/16 |
| Video generation time | <5 min | — |
| Script quality | >80% usable | — |
| Subtitle sync accuracy | >95% | — |
| User completion rate | >60% | — |
| Tests passing | — | 110 |

## Accumulated Context

### Decisions Made
| Decision | Rationale | Date |
|----------|-----------|------|
| Remotion for video rendering | Web tech stack, programmable, React component model | 2026-03-30 |
| edge-tts as default TTS | Free, high quality, async-native Python SDK | 2026-03-30 |
| litellm for LLM gateway | Avoids single-model lock-in, supports LM Studio/OpenAI/local | 2026-03-30 |
| Celery+Redis async queue | Mature distributed queue, separate queues per pipeline stage | 2026-03-30 |
| Pexels as primary stock API | Simpler, video support, good API | 2026-03-30 |
| 9 phases, fine granularity | Matches natural build sequence along critical path | 2026-03-30 |
| Single pipeline task (not chain) | Simpler debugging, reliable stage tracking via render_props | 2026-04-01 |
| Vanilla HTML/CSS/JS for web UI | Zero dependencies, fast load, simple deployment | 2026-04-01 |
| Polling over SSE for frontend | Simpler frontend, adequate for 2s update frequency | 2026-04-01 |

### Risks to Monitor
| Risk | Mitigation |
|------|------------|
| edge-tts API breakage | Azure TTS fallback via litellm-style abstraction |
| Chinese stock content gap | AI-generated imagery (DALL-E/Midjourney) for v2 |
| Sync video gen blocks API | Always use Celery; time_limit=600 |
| FFmpeg string concatenation | Use ffmpeg-python for type-safe filter graphs |

### Current Todos
- [x] Execute Phase 1 — all 3 plans ✓
- [x] Execute Phase 2 — all 5 plans ✓
- [x] Execute Phase 3 — all 2 plans ✓
- [x] Execute Phase 4 — all 2 plans ✓
- [x] Execute Phase 5 — all 3 plans ✓
- [x] Execute Phase 6 — all 4 plans ✓
- [x] Execute Phase 7 — all 3 plans ✓
- [x] Execute Phase 8 — all 4 plans ✓

## Session Continuity

**Last session**: Phase 8 execution complete (2026-04-01)
**Next action**: v1 MVP complete — all 8 phases done. Manual testing of web UI at http://localhost:8000/
**Context**: Phase 8 delivered: REST API (6 endpoints: generate, get, status, download, list, SSE stream), OrchestratorService (pipeline lifecycle), full pipeline Celery task (5 stages: script→audio→subtitles→media→compose), TTS task wrapper, single-page web UI (dark theme, progress stepper, video preview, download), 20 API tests (110 total passing). Web UI accessible at /web/ with root redirect.

---

*Updated: 2026-04-01 after Phase 7 execution*
