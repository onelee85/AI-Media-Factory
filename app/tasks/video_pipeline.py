"""Celery task for end-to-end video generation pipeline.

Runs all pipeline stages sequentially within a single Celery task:
script generation → TTS → subtitles → media matching → compose.

Each stage updates the Video record's render_props with current stage
for real-time progress tracking via the REST API.
"""
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from app.celery_app import celery_app
from app.db import async_session
from app.models.audio import AudioFile
from app.models.script import Script
from app.models.script_media import ScriptMedia
from app.models.subtitle import Subtitle
from app.models.video import Video
from app.services.compose_service import ComposeService, ComposeServiceError
from app.services.script_generator import script_generator_service
from app.services.subtitle_service import SubtitleService
from app.services.tts_service import TTSService, TTSServiceError
from app.storage import StorageService
from sqlalchemy import select


def _update_stage_sync(video_id: str, stage: str, session):
    """Update Video.render_props with current pipeline stage."""
    # This is called from sync context within asyncio.run
    video = session.get(Video, video_id)
    if video:
        props = video.render_props or {}
        props["stage"] = stage
        video.render_props = props


@celery_app.task(bind=True, name="app.tasks.pipeline.generate_video", acks_late=True)
def generate_video_pipeline_task(
    self,
    video_id: str,
    prompt: str,
    title: str = "",
    voice: str = "zh-CN-YunxiNeural",
):
    """Run the full video generation pipeline sequentially.

    Stages: script → audio → subtitles → media → compose.
    Updates Video.render_props.stage after each stage for progress tracking.

    Args:
        video_id: UUID string of pre-created Video record.
        prompt: User's topic/prompt for video generation.
        title: Optional video title.
        voice: TTS voice name.

    Returns:
        Dict with video_id, status, file_path (if completed).
    """
    import asyncio

    return asyncio.run(
        _run_pipeline_async(
            video_id=video_id,
            prompt=prompt,
            title=title,
            voice=voice,
        )
    )


async def _run_pipeline_async(
    video_id: str,
    prompt: str,
    title: str,
    voice: str,
):
    """Async core of the pipeline task."""
    storage = StorageService()

    async with async_session() as session:
        # Fetch pre-created Video and related records
        result = await session.execute(select(Video).where(Video.id == video_id))
        video = result.scalar_one_or_none()
        if not video:
            return {"error": f"Video {video_id} not found"}

        # Fetch related records
        script_result = await session.execute(
            select(Script).where(Script.id == video.script_id)
        )
        script = script_result.scalar_one_or_none()

        audio_result = await session.execute(
            select(AudioFile).where(AudioFile.id == video.audio_id)
        )
        audio = audio_result.scalar_one_or_none()

        subtitle_result = await session.execute(
            select(Subtitle).where(Subtitle.id == video.subtitle_id)
        )
        subtitle = subtitle_result.scalar_one_or_none()

        if not script or not audio or not subtitle:
            video.status = "failed"
            video.error = "Missing related records (script/audio/subtitle)"
            await session.flush()
            return {"error": "Missing related records"}

        stage_timings: dict[str, float] = {}
        pipeline_start = time.perf_counter()

        try:
            # ==================== Stage 1: Script Generation ====================
            video.status = "running"
            video.render_props = {"stage": "script"}
            script.status = "generating"
            await session.flush()

            stage_start = time.perf_counter()
            generation_result = script_generator_service.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=2000,
            )

            # Format script content
            content = _format_script_content(generation_result)
            script.content = content
            script.title = generation_result.get("title", script.title)
            script.model = generation_result.get("model", "")
            script.status = "completed"
            script.completed_at = datetime.now(timezone.utc)
            script.script_metadata = {
                "sections": generation_result.get("sections", []),
                "summary": generation_result.get("summary", ""),
                "usage": generation_result.get("usage", {}),
                "provider_used": generation_result.get("provider", ""),
            }
            await session.flush()

            stage_timings["script"] = round(time.perf_counter() - stage_start, 2)

            # ==================== Stage 2: TTS (Audio) ====================
            video.render_props = {"stage": "audio"}
            audio.status = "generating"
            await session.flush()

            stage_start = time.perf_counter()
            tts_service = TTSService()
            audio_dir = storage.audio_dir(str(script.id))
            audio_path = audio_dir / f"{audio.id}.mp3"

            # Determine language from voice
            language = "zh" if "zh" in voice else "en"

            tts_result = await tts_service.generate(
                text=script.content,
                voice=voice,
                language=language,
                output_path=str(audio_path),
            )

            audio.file_path = tts_result["audio_path"]
            audio.file_size_bytes = (
                Path(tts_result["audio_path"]).stat().st_size
                if Path(tts_result["audio_path"]).exists()
                else 0
            )
            audio.duration_seconds = tts_result.get("duration_seconds", 0.0)
            audio.word_timing = tts_result.get("word_timing", [])
            audio.status = "completed"
            audio.completed_at = datetime.now(timezone.utc)
            await session.flush()

            stage_timings["audio"] = round(time.perf_counter() - stage_start, 2)

            # ==================== Stage 3: Subtitles ====================
            video.render_props = {"stage": "subtitles"}
            subtitle.status = "generating"
            await session.flush()

            stage_start = time.perf_counter()
            subtitle_service = SubtitleService()
            word_timing = tts_result.get("word_timing", [])

            if word_timing:
                sub_result = subtitle_service.generate(
                    word_timing=word_timing,
                    formats=["srt"],
                    title=script.title,
                )

                srt_content = sub_result.get("srt_content", "")
                srt_filename = f"{audio.id}.srt"
                srt_storage_path = storage.subtitle_dir() / srt_filename
                storage.write_bytes(srt_storage_path, srt_content.encode("utf-8"))

                subtitle.format = "srt"
                subtitle.file_path = str(srt_storage_path)
                subtitle.content = srt_content
                subtitle.word_count = sub_result.get("word_count", 0)
                subtitle.line_count = sub_result.get("line_count", 0)
                subtitle.status = "completed"
                subtitle.completed_at = datetime.now(timezone.utc)
            else:
                subtitle.content = ""
                subtitle.status = "completed"
                subtitle.completed_at = datetime.now(timezone.utc)

            await session.flush()

            stage_timings["subtitles"] = round(time.perf_counter() - stage_start, 2)

            # ==================== Stage 4: Media Matching (optional) ====================
            video.render_props = {"stage": "media"}
            await session.flush()

            stage_start = time.perf_counter()
            image_paths: list[str] = []
            try:
                # Try to match media if Pexels API key is available
                import os
                api_key = os.getenv("PEXELS_API_KEY", "")
                if api_key and script.script_metadata and script.script_metadata.get("sections"):
                    from app.services.media_service import (
                        KeywordExtractor,
                        PexelsClient,
                        StockMediaService,
                    )

                    pexels_client = PexelsClient(api_key=api_key)
                    keyword_extractor = KeywordExtractor()
                    media_service = StockMediaService(
                        pexels_client, keyword_extractor, storage
                    )

                    sections = script.script_metadata.get("sections", [])
                    save_dir = storage.image_dir() / str(script.id)

                    section_results = media_service.match_images_to_script(
                        script_sections=sections,
                        save_dir=save_dir,
                        images_per_section=1,
                    )

                    # Build matched_images and collect paths
                    matched_images = []
                    for idx, paths in enumerate(section_results):
                        keywords = keyword_extractor.extract_keywords(sections[idx])
                        matched_images.append({
                            "section_index": idx,
                            "image_paths": [str(p) for p in paths],
                            "keywords": keywords,
                        })
                        for p in paths:
                            if Path(p).exists():
                                image_paths.append(str(p))

                    # Create ScriptMedia record
                    script_media = ScriptMedia(
                        script_id=script.id,
                        matched_images=matched_images,
                        status="completed",
                        completed_at=datetime.now(timezone.utc),
                    )
                    session.add(script_media)

                    pexels_client.close()
            except Exception:
                # Media matching is optional — degrade gracefully
                image_paths = []

            await session.flush()

            stage_timings["media"] = round(time.perf_counter() - stage_start, 2)

            # ==================== Stage 5: Compose ====================
            video.render_props = {"stage": "compose"}
            video.status = "rendering"
            await session.flush()

            stage_start = time.perf_counter()
            compose_service = ComposeService(storage=storage)
            render_dir = storage.render_dir(str(script.id))
            output_path = render_dir / f"{video_id}.mp4"

            compose_service.compose(
                audio_file_path=Path(tts_result["audio_path"]),
                subtitle_content=subtitle.content or "",
                output_path=output_path,
                title=title or script.title,
                images=image_paths if image_paths else None,
            )

            # ==================== Done ====================
            stage_timings["compose"] = round(time.perf_counter() - stage_start, 2)
            stage_timings["total"] = round(time.perf_counter() - pipeline_start, 2)
            file_size = output_path.stat().st_size if output_path.exists() else 0

            video.status = "completed"
            video.file_path = str(output_path)
            video.file_size_bytes = file_size
            video.completed_at = datetime.now(timezone.utc)
            video.render_props = {"stage": "completed", "timing": stage_timings}
            await session.flush()

            return {
                "video_id": video_id,
                "status": "completed",
                "file_path": str(output_path),
                "file_size_bytes": file_size,
                "timing": stage_timings,
            }

        except (TTSServiceError, ComposeServiceError) as exc:
            stage_timings["total"] = round(time.perf_counter() - pipeline_start, 2)
            video.status = "failed"
            video.error = str(exc)
            video.render_props = {"stage": "failed", "timing": stage_timings}
            await session.flush()
            return {
                "video_id": video_id,
                "status": "failed",
                "error": str(exc),
                "timing": stage_timings,
            }

        except Exception as exc:
            stage_timings["total"] = round(time.perf_counter() - pipeline_start, 2)
            video.status = "failed"
            video.error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            video.render_props = {"stage": "failed", "timing": stage_timings}
            await session.flush()
            return {
                "video_id": video_id,
                "status": "failed",
                "error": str(exc),
                "timing": stage_timings,
            }


def _format_script_content(result: dict) -> str:
    """Convert structured script JSON to human-readable markdown."""
    lines = [f"# {result.get('title', 'Untitled Script')}", ""]

    for section in result.get("sections", []):
        heading = section.get("heading", "Section")
        content = section.get("content", "")
        duration = section.get("duration_estimate_sec")
        duration_str = f" (~{duration}s)" if duration else ""
        lines.append(f"## {heading}{duration_str}")
        lines.append("")
        lines.append(content)
        lines.append("")

    summary = result.get("summary", "")
    if summary:
        lines.append("---")
        lines.append(f"**Summary:** {summary}")

    return "\n".join(lines)
