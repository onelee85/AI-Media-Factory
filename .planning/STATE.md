# STATE — AI-Media-Factory

## Project Reference

- **Core Value**: "一键出片" — one-click video generation from text
- **Current Focus**: v1 MVP — core pipeline from text input to video download
- **Critical Path**: Script Gen → TTS → Subtitles → Remotion Composition → Export

## Current Position

- **Phase**: 6 (complete)
- **Plan**: 06-04 (all plans executed)
- **Status**: Phase 6 complete — Remotion project scaffolded, SSR render pipeline, preview player, Python integration via ComposeService + Celery
- **Progress**: ██████████████████░░ 7/9 phases (6 complete, 1 ready)

## Performance Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Phases completed | 9 | 5 |
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

## Session Continuity

**Last session**: Phase 6 execution complete (2026-03-31)
**Next action**: `/gsd-execute-phase 7` — Execute Phase 7
**Context**: Phase 6 delivered: Remotion scaffold, VideoComposition with audio/subtitles/background layers, SRT parser, SSR render.mjs script, preview player with FastAPI endpoint, Video model, ComposeService, and Celery compose_video_task. Full pipeline from Python backend → Node.js Remotion render → MP4 output is now wired.

---

*Updated: 2026-03-31 after Phase 6 execution*
