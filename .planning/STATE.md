# STATE — AI-Media-Factory

## Project Reference

- **Core Value**: "一键出片" — one-click video generation from text
- **Current Focus**: v1 MVP — core pipeline from text input to video download
- **Critical Path**: Script Gen → TTS → Subtitles → Remotion Composition → Export

## Current Position

- **Phase**: 9 (complete)
- **Plan**: 05 (complete)
- **Status**: Phase 9 complete — Quality Assurance & Performance, 5 plans in 2 waves
- **Progress**: █████████████████████████ 9/9 phases (9 complete)

## Performance Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Phases completed | 9 | 9 |
| Requirements mapped | 20/20 | 20/20 |
| Video generation time | <5 min | Instrumented |
| Script quality | >80% usable | Validated |
| Subtitle sync accuracy | >95% | Validated |
| User completion rate | >60% | Tracked |
| Tests passing | — | 157 |

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
- [x] Execute Phase 9 — all 5 plans ✓

## Session Continuity

**Last session**: Phase 9 execution complete (2026-04-01)
**Next action**: v1 MVP complete — all 9 phases done. Manual testing of web UI at http://localhost:8000/web/
**Context**: Phase 9 delivered: pipeline timing instrumentation (per-stage time.perf_counter() in render_props), benchmark suite (runner + report generator), script quality test suite (13 tests, QUAL-02 >80%), subtitle sync accuracy test suite (11 tests, QUAL-03 >95%), UX completion tracking (flowTracker with 5-step funnel), Celery time_limit=300 (QUAL-01 enforcement), enhanced SYSTEM_PROMPT with quality validation (MIN_CONTENT_LENGTH=50), punctuation-based subtitle line breaks, error recovery (3-retry polling, timeout handling, Chinese error messages), download prominence ("生成新视频" button), visual polish (progress transitions, checkmark fade-in, error shake). 157 tests passing (47 new from Phase 9). All quality targets instrumented and validated.

---

*Updated: 2026-04-01 after Phase 9 execution*
