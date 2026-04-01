"""OrchestratorService — manages the full video generation pipeline lifecycle.

Creates Project, Script, AudioFile, Subtitle, Video records upfront,
then dispatches a single Celery task that runs all pipeline stages
sequentially with per-stage status tracking.
"""

from sqlalchemy import select

from app.db import async_session
from app.models.audio import AudioFile
from app.models.project import Project
from app.models.script import Script
from app.models.subtitle import Subtitle
from app.models.video import Video


class OrchestratorError(Exception):
    """Pipeline orchestration error."""
    pass


class OrchestratorService:
    """Orchestrates the full video generation pipeline.

    Creates all DB records upfront and dispatches a single Celery task
    that runs stages sequentially: script → audio → subtitles → media → compose.
    """

    async def start_pipeline(
        self,
        prompt: str,
        title: str = "",
        voice: str = "zh-CN-YunxiNeural",
    ) -> dict:
        """Start a new video generation pipeline.

        Creates Project, Script, AudioFile, Subtitle, Video records,
        then dispatches the pipeline Celery task.

        Args:
            prompt: User's topic/prompt for video generation.
            title: Optional video title.
            voice: TTS voice name.

        Returns:
            Dict with video_id, celery_task_id, status.
        """
        # Import here to avoid circular imports
        from app.tasks.video_pipeline import generate_video_pipeline_task

        async with async_session() as session:
            # 1. Create Project
            project = Project(
                name=title or "Untitled Video",
                status="active",
                config={"prompt": prompt, "voice": voice},
            )
            session.add(project)
            await session.flush()

            # 2. Create Script (placeholder — pipeline task fills it in)
            script = Script(
                project_id=project.id,
                title=title or "Untitled Script",
                prompt=prompt,
                status="pending",
            )
            session.add(script)
            await session.flush()

            # 3. Create AudioFile (placeholder — pipeline task fills it in)
            audio = AudioFile(
                script_id=script.id,
                voice=voice,
                language="zh",
                file_path="",
                status="pending",
            )
            session.add(audio)
            await session.flush()

            # 4. Create Subtitle (placeholder — pipeline task fills it in)
            subtitle = Subtitle(
                script_id=script.id,
                audio_id=audio.id,
                format="srt",
                file_path="",
                content="",
                status="pending",
            )
            session.add(subtitle)
            await session.flush()

            # 5. Create Video record
            video = Video(
                script_id=script.id,
                audio_id=audio.id,
                subtitle_id=subtitle.id,
                file_path="",
                status="pending",
                render_props={"stage": "script"},
            )
            session.add(video)
            await session.flush()

            video_id = str(video.id)

            # 6. Dispatch Celery pipeline task
            celery_result = generate_video_pipeline_task.delay(
                video_id=video_id,
                prompt=prompt,
                title=title or "",
                voice=voice,
            )

            # 7. Update Video with celery_task_id
            video.celery_task_id = celery_result.id
            video.status = "queued"
            await session.flush()
            await session.commit()

            return {
                "video_id": video_id,
                "celery_task_id": celery_result.id,
                "status": "queued",
            }

    async def get_video_with_details(self, video_id: str) -> dict | None:
        """Get video record with related script, audio, subtitle details.

        Args:
            video_id: UUID string of Video record.

        Returns:
            Dict with video + nested script/audio/subtitle data, or None.
        """
        async with async_session() as session:
            result = await session.execute(
                select(Video).where(Video.id == video_id)
            )
            video = result.scalar_one_or_none()
            if not video:
                return None

            # Fetch related records
            script_result = await session.execute(
                select(Script).where(Script.id == video.script_id)
            )
            script = script_result.scalar_one_or_none()

            audio_result = await session.execute(
                select(AudioFile).where(AudioFile.id == video.audio_id)
            )
            audio = audio_result.scalar_one_or_none()

            subtitle = None
            if video.subtitle_id:
                subtitle_result = await session.execute(
                    select(Subtitle).where(Subtitle.id == video.subtitle_id)
                )
                subtitle = subtitle_result.scalar_one_or_none()

            return {
                "id": str(video.id),
                "script_id": str(video.script_id),
                "audio_id": str(video.audio_id),
                "subtitle_id": str(video.subtitle_id) if video.subtitle_id else None,
                "celery_task_id": video.celery_task_id,
                "file_path": video.file_path,
                "file_size_bytes": video.file_size_bytes,
                "duration_seconds": video.duration_seconds,
                "width": video.width,
                "height": video.height,
                "codec": video.codec,
                "render_props": video.render_props,
                "status": video.status,
                "error": video.error,
                "created_at": video.created_at.isoformat() if video.created_at else None,
                "updated_at": video.updated_at.isoformat() if video.updated_at else None,
                "completed_at": video.completed_at.isoformat() if video.completed_at else None,
                "script": {
                    "id": str(script.id),
                    "title": script.title,
                    "status": script.status,
                    "error": script.error,
                } if script else None,
                "audio": {
                    "id": str(audio.id),
                    "voice": audio.voice,
                    "duration_seconds": audio.duration_seconds,
                    "status": audio.status,
                } if audio else None,
                "subtitle": {
                    "id": str(subtitle.id),
                    "format": subtitle.format,
                    "status": subtitle.status,
                } if subtitle else None,
            }


# Module-level singleton
orchestrator_service = OrchestratorService()
