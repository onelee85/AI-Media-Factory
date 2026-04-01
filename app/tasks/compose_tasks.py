"""Celery task for async video composition and rendering.

Loads audio + subtitle data, invokes Remotion render via subprocess,
tracks Video record status in database.
"""
import traceback
from datetime import datetime, timezone
from pathlib import Path

from app.celery_app import celery_app
from app.db import async_session
from app.models.audio import AudioFile
from app.models.script_media import ScriptMedia
from app.models.subtitle import Subtitle
from app.models.video import Video
from app.services.compose_service import ComposeService, ComposeServiceError
from app.storage import StorageService
from sqlalchemy import select


@celery_app.task(bind=True, name="app.tasks.compose.video", acks_late=True)
def compose_video_task(
    self,
    audio_id: str,
    subtitle_id: str | None = None,
    title: str = "",
):
    """Celery task: compose and render a video from audio + subtitles.

    Loads AudioFile and Subtitle records, invokes ComposeService to render
    via Remotion, and tracks the Video record status in the database.

    Args:
        audio_id: UUID string of AudioFile record.
        subtitle_id: UUID string of Subtitle record (optional, finds latest SRT).
        title: Optional title text for video overlay.

    Returns:
        Dict with video_id, status, file_path, file_size_bytes.
    """
    import asyncio

    return asyncio.run(
        _compose_video_async(
            audio_id=audio_id,
            subtitle_id=subtitle_id,
            title=title,
        )
    )


async def _compose_video_async(
    audio_id: str,
    subtitle_id: str | None,
    title: str,
):
    """Async core of the video composition task."""
    storage = StorageService()
    service = ComposeService(storage=storage)

    async with async_session() as session:
        # Fetch the audio record
        result = await session.execute(
            select(AudioFile).where(AudioFile.id == audio_id)
        )
        audio = result.scalar_one_or_none()
        if not audio:
            return {"error": f"AudioFile {audio_id} not found"}

        if audio.status != "completed":
            return {
                "error": f"AudioFile {audio_id} status is '{audio.status}', expected 'completed'"
            }

        # Fetch subtitle
        subtitle = None
        if subtitle_id:
            result = await session.execute(
                select(Subtitle).where(Subtitle.id == subtitle_id)
            )
            subtitle = result.scalar_one_or_none()
        else:
            # Find latest completed SRT subtitle for this audio
            result = await session.execute(
                select(Subtitle)
                .where(Subtitle.audio_id == audio_id, Subtitle.format == "srt")
                .order_by(Subtitle.created_at.desc())
                .limit(1)
            )
            subtitle = result.scalar_one_or_none()

        if not subtitle or subtitle.status != "completed":
            return {"error": "No completed subtitle found for this audio"}

        if not subtitle.content:
            return {"error": "Subtitle has no content"}

        # Load matched images from ScriptMedia (Phase 7 integration)
        image_paths: list[str] = []
        try:
            result = await session.execute(
                select(ScriptMedia)
                .where(
                    ScriptMedia.script_id == audio.script_id,
                    ScriptMedia.status == "completed",
                )
                .order_by(ScriptMedia.created_at.desc())
                .limit(1)
            )
            script_media = result.scalar_one_or_none()
            if script_media and script_media.matched_images:
                for section_entry in script_media.matched_images:
                    for img_path in section_entry.get("image_paths", []):
                        # Verify file exists before adding
                        if Path(img_path).exists():
                            image_paths.append(img_path)
        except Exception:
            # ScriptMedia table may not exist yet — degrade gracefully
            image_paths = []

        # Create Video record
        video = Video(
            script_id=audio.script_id,
            audio_id=audio.id,
            subtitle_id=subtitle.id,
            status="rendering",
            render_props={
                "audio_id": str(audio.id),
                "subtitle_id": str(subtitle.id),
                "title": title,
            },
        )
        session.add(video)
        await session.flush()
        video_id = str(video.id)

        try:
            # Build file paths
            audio_path = storage.audio_dir(str(audio.script_id)) / audio.file_path
            output_dir = storage.render_dir(str(audio.script_id))
            output_path = output_dir / f"{video_id}.mp4"

            # Invoke render
            result = service.compose(
                audio_file_path=audio_path,
                subtitle_content=subtitle.content,
                output_path=output_path,
                title=title,
                images=image_paths if image_paths else None,
            )

            # Get file size
            file_size = output_path.stat().st_size if output_path.exists() else 0

            # Update Video record
            video.status = "completed"
            video.file_path = str(output_path)
            video.file_size_bytes = file_size
            video.completed_at = datetime.now(timezone.utc)
            await session.flush()

            return {
                "video_id": video_id,
                "status": "completed",
                "file_path": str(output_path),
                "file_size_bytes": file_size,
            }

        except ComposeServiceError as exc:
            video.status = "failed"
            video.error = str(exc)
            await session.flush()
            return {
                "video_id": video_id,
                "status": "failed",
                "error": str(exc),
            }

        except Exception as exc:
            video.status = "failed"
            video.error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            await session.flush()
            return {
                "video_id": video_id,
                "status": "failed",
                "error": str(exc),
            }
