# STATE — AI-Media-Factory

## Project Reference

- **Core Value**: "一键出片" — one-click video generation from text
- **Current Focus**: v1 MVP — core pipeline from text input to video download
- **Critical Path**: Script Gen → TTS → Subtitles → Remotion Composition → Export

## Current Position

- **Phase**: 7 (complete)
- **Plan**: 07-03 (all plans executed)
- **Status**: Phase 7 complete — Pexels API client, keyword extraction, stock media matching pipeline, compose integration, 13 tests passing
- **Progress**: ████████████████████░ 8/9 phases (7 complete, 1 ready)

## Performance Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Phases completed | 9 | 7 |
| Requirements mapped | 16/16 | 16/16 |
| Video generation time | <5 min | — |
| Script quality | >80% usable | — |
| Subtitle sync accuracy | >95% | — |
| User completion rate | >60% | — |

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

## Session Continuity

**Last session**: Phase 7 execution complete (2026-04-01)
**Next action**: `/gsd-execute-phase 8` — Execute Phase 8 (Web Interface & REST API)
**Context**: Phase 7 delivered: PexelsClient (search/download via httpx), KeywordExtractor (English/Chinese), StockMediaService (orchestration), ScriptMedia model (status tracking + JSONB results), match_media_task (async Celery on media queue), compose pipeline integration (loads matched images, graceful degradation), 13 passing tests for keyword extraction.

---

*Updated: 2026-04-01 after Phase 7 execution*
