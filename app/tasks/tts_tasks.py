"""Celery task for async text-to-speech generation.

Wraps TTSService to generate audio from script content and persist
AudioFile records with word-level timing data.
"""
import traceback
from datetime import datetime, timezone
from pathlib import Path

from app.celery_app import celery_app
from app.db import async_session
from app.models.audio import AudioFile
from app.models.script import Script
from app.services.tts_service import TTSService, TTSServiceError
from app.storage import StorageService
from sqlalchemy import select


@celery_app.task(bind=True, name="app.tasks.tts.generate", acks_late=True)
def generate_audio_task(
    self,
    script_id: str,
    voice: str = "zh-CN-YunxiNeural",
    language: str = "zh",
):
    """Celery task: generate audio from script content via TTS.

    Loads Script content, calls TTSService to synthesize audio,
    creates AudioFile record with word_timing data.

    Args:
        script_id: UUID string of Script record.
        voice: edge-tts voice name.
        language: Language code ("zh" or "en").

    Returns:
        Dict with audio_id, status, file_path, duration_seconds.
    """
    import asyncio

    return asyncio.run(
        _generate_audio_async(
            script_id=script_id,
            voice=voice,
            language=language,
            task_id=self.request.id if hasattr(self, "request") else None,
        )
    )


async def _generate_audio_async(
    script_id: str,
    voice: str,
    language: str,
    task_id: str | None,
):
    """Async core of the TTS generation task."""
    storage = StorageService()
    tts_service = TTSService()

    async with async_session() as session:
        # Fetch the script record
        result = await session.execute(
            select(Script).where(Script.id == script_id)
        )
        script = result.scalar_one_or_none()
        if not script:
            return {"error": f"Script {script_id} not found"}

        if not script.content:
            return {"error": f"Script {script_id} has no content"}

        # Create AudioFile record
        audio = AudioFile(
            script_id=script.id,
            celery_task_id=task_id,
            voice=voice,
            language=language,
            file_path="",  # Will be set after generation
            status="generating",
        )
        session.add(audio)
        await session.flush()
        audio_id = str(audio.id)

        try:
            # Prepare output path
            audio_dir = storage.audio_dir(str(script_id))
            output_path = audio_dir / f"{audio_id}.mp3"

            # Generate audio
            result = await tts_service.generate(
                text=script.content,
                voice=voice,
                language=language,
                output_path=str(output_path),
            )

            # Update AudioFile record
            audio.file_path = result["audio_path"]
            audio.file_size_bytes = (
                Path(result["audio_path"]).stat().st_size
                if Path(result["audio_path"]).exists()
                else 0
            )
            audio.duration_seconds = result.get("duration_seconds", 0.0)
            audio.word_timing = result.get("word_timing", [])
            audio.status = "completed"
            audio.completed_at = datetime.now(timezone.utc)
            await session.flush()

            return {
                "audio_id": audio_id,
                "status": "completed",
                "file_path": result["audio_path"],
                "duration_seconds": result.get("duration_seconds", 0.0),
            }

        except TTSServiceError as exc:
            audio.status = "failed"
            audio.error = str(exc)
            await session.flush()
            return {
                "audio_id": audio_id,
                "status": "failed",
                "error": str(exc),
            }

        except Exception as exc:
            audio.status = "failed"
            audio.error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            await session.flush()
            return {
                "audio_id": audio_id,
                "status": "failed",
                "error": str(exc),
            }
