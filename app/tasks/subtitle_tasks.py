"""Celery task for async subtitle generation from TTS word timing.

Takes an audio_id, loads word_timing from AudioFile, generates SRT/ASS
subtitles, and persists files to the filesystem.
"""
import traceback
from datetime import datetime, timezone
from pathlib import Path

from app.celery_app import celery_app
from app.db import async_session
from app.models.audio import AudioFile
from app.models.subtitle import Subtitle
from app.services.subtitle_service import SubtitleService
from app.storage import StorageService
from sqlalchemy import select


@celery_app.task(bind=True, name="app.tasks.subtitles.generate", acks_late=True)
def generate_subtitles_task(
    self,
    audio_id: str,
    formats: list[str] | None = None,
    title: str = "Subtitle",
):
    """Celery task: generate subtitle files from audio word timing.

    Loads AudioFile record, extracts word_timing, generates SRT/ASS
    subtitles, writes to filesystem, and tracks status in DB.

    Args:
        audio_id: UUID string of AudioFile record.
        formats: List of formats to generate (default: ["srt", "ass"]).
        title: Title for ASS header.

    Returns:
        Dict with subtitle_id, status, srt_path, ass_path, word_count, line_count.
    """
    import asyncio

    if formats is None:
        formats = ["srt", "ass"]

    return asyncio.run(
        _generate_subtitles_async(
            audio_id=audio_id,
            formats=formats,
            title=title,
        )
    )


async def _generate_subtitles_async(
    audio_id: str,
    formats: list[str],
    title: str,
):
    """Async core of the subtitle generation task."""
    storage = StorageService()
    service = SubtitleService()

    async with async_session() as session:
        # Fetch the audio record
        result = await session.execute(
            select(AudioFile).where(AudioFile.id == audio_id)
        )
        audio = result.scalar_one_or_none()
        if not audio:
            return {"error": f"AudioFile {audio_id} not found"}

        if audio.status != "completed":
            return {"error": f"AudioFile {audio_id} status is '{audio.status}', expected 'completed'"}

        # Extract word_timing from JSONB
        word_timing = audio.word_timing
        if not word_timing:
            return {"error": f"AudioFile {audio_id} has no word_timing data"}

        # Ensure word_timing is a list
        if isinstance(word_timing, dict):
            word_timing = word_timing.get("words", [])

        # Create subtitle record
        subtitle = Subtitle(
            script_id=audio.script_id,
            audio_id=audio.id,
            format=formats[0],  # Primary format
            file_path="",  # Will be set below
            content="",
            status="pending",
        )
        session.add(subtitle)
        await session.flush()

        try:
            # Generate subtitles
            gen_result = service.generate(
                word_timing=word_timing,
                formats=formats,
                title=title,
            )

            srt_path = None
            ass_path = None

            # Write SRT file
            if "srt" in formats and gen_result.get("srt_content"):
                srt_filename = f"{audio_id}.srt"
                srt_storage_path = storage.subtitle_dir() / srt_filename
                storage.write_bytes(
                    srt_storage_path,
                    gen_result["srt_content"].encode("utf-8"),
                )
                srt_path = str(srt_storage_path)

            # Write ASS file
            if "ass" in formats and gen_result.get("ass_content"):
                ass_filename = f"{audio_id}.ass"
                ass_storage_path = storage.subtitle_dir() / ass_filename
                storage.write_bytes(
                    ass_storage_path,
                    gen_result["ass_content"].encode("utf-8"),
                )
                ass_path = str(ass_storage_path)

            # Update subtitle record (SRT as primary)
            subtitle.format = "srt"
            subtitle.file_path = srt_path or ass_path or ""
            subtitle.content = gen_result.get("srt_content") or gen_result.get("ass_content") or ""
            subtitle.word_count = gen_result["word_count"]
            subtitle.line_count = gen_result["line_count"]
            subtitle.status = "completed"
            subtitle.completed_at = datetime.now(timezone.utc)

            # Also create ASS record if both formats requested
            if "ass" in formats and "srt" in formats and ass_path:
                ass_subtitle = Subtitle(
                    script_id=audio.script_id,
                    audio_id=audio.id,
                    format="ass",
                    file_path=ass_path,
                    content=gen_result.get("ass_content", ""),
                    word_count=gen_result["word_count"],
                    line_count=gen_result["line_count"],
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                )
                session.add(ass_subtitle)

            await session.flush()

            return {
                "subtitle_id": str(subtitle.id),
                "status": "completed",
                "srt_path": srt_path,
                "ass_path": ass_path,
                "word_count": gen_result["word_count"],
                "line_count": gen_result["line_count"],
            }

        except Exception as exc:
            subtitle.status = "failed"
            subtitle.error = f"{type(exc).__name__}: {exc}"
            await session.flush()
            return {
                "subtitle_id": str(subtitle.id),
                "status": "failed",
                "error": str(exc),
            }
