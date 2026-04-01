"""REST API endpoints for video generation lifecycle.

Provides endpoints to create, track, download, and list videos.
Supports both polling and SSE streaming for real-time progress updates.
"""
import asyncio
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.audio import AudioFile
from app.models.script import Script
from app.models.script_media import ScriptMedia
from app.models.subtitle import Subtitle
from app.models.video import Video
from app.services.orchestrator import orchestrator_service

videos_router = APIRouter(prefix="/api/videos", tags=["videos"])


# --- Request / Response schemas ---


class VideoGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000, description="Topic or brief for the video")
    title: str = Field(default="", max_length=300, description="Optional video title")
    voice: str = Field(default="zh-CN-YunxiNeural", description="TTS voice name")


class VideoGenerateResponse(BaseModel):
    video_id: str
    status: str
    celery_task_id: str | None


class VideoStatusResponse(BaseModel):
    video_id: str
    status: str
    stage: str
    error: str | None
    created_at: str | None
    completed_at: str | None


class VideoDetailResponse(BaseModel):
    id: str
    script_id: str
    audio_id: str
    subtitle_id: str | None
    celery_task_id: str | None
    file_path: str
    file_size_bytes: int | None
    duration_seconds: float | None
    width: int
    height: int
    codec: str
    render_props: dict | None
    status: str
    error: str | None
    created_at: str | None
    updated_at: str | None
    completed_at: str | None
    script: dict | None
    audio: dict | None
    subtitle: dict | None


class VideoListItem(BaseModel):
    id: str
    script_id: str
    status: str
    file_path: str
    file_size_bytes: int | None
    duration_seconds: float | None
    error: str | None
    created_at: str | None
    completed_at: str | None


# --- Status resolution ---


async def _resolve_stage(db: AsyncSession, video: Video) -> str:
    """Determine the current pipeline stage for a video.

    Resolution order:
    1. If video.status == "completed" → "completed"
    2. If video.status == "failed" → "failed"
    3. Otherwise check related records for current stage.
    """
    if video.status == "completed":
        return "completed"
    if video.status == "failed":
        return "failed"

    # Check render_props for stage hint
    if video.render_props and "stage" in video.render_props:
        stage = video.render_props["stage"]
        if stage in ("script", "audio", "subtitles", "media", "compose", "completed", "failed"):
            return stage

    # Fallback: check related record statuses
    # Script status
    script_result = await db.execute(
        select(Script).where(Script.id == video.script_id)
    )
    script = script_result.scalar_one_or_none()
    if not script or script.status in ("pending", "generating", "queued"):
        return "script"

    # Audio status
    audio_result = await db.execute(
        select(AudioFile).where(AudioFile.id == video.audio_id)
    )
    audio = audio_result.scalar_one_or_none()
    if not audio or audio.status in ("pending", "generating"):
        return "audio"

    # Subtitle status
    if video.subtitle_id:
        subtitle_result = await db.execute(
            select(Subtitle).where(Subtitle.id == video.subtitle_id)
        )
        subtitle = subtitle_result.scalar_one_or_none()
        if not subtitle or subtitle.status in ("pending", "generating"):
            return "subtitles"

    # Media matching status (optional)
    media_result = await db.execute(
        select(ScriptMedia)
        .where(ScriptMedia.script_id == video.script_id)
        .order_by(ScriptMedia.created_at.desc())
        .limit(1)
    )
    script_media = media_result.scalar_one_or_none()
    if script_media and script_media.status in ("pending", "matching"):
        return "media"

    # If video is rendering
    if video.status in ("rendering", "running"):
        return "compose"

    return "compose"


# --- Endpoints ---


@videos_router.post("/generate", response_model=VideoGenerateResponse, status_code=201)
async def generate_video(body: VideoGenerateRequest):
    """Start a new video generation pipeline.

    Creates all DB records and dispatches the pipeline Celery task.
    Returns immediately with video_id for polling.
    """
    result = await orchestrator_service.start_pipeline(
        prompt=body.prompt,
        title=body.title,
        voice=body.voice,
    )
    return VideoGenerateResponse(**result)


@videos_router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full video details including related script, audio, subtitle status."""
    details = await orchestrator_service.get_video_with_details(str(video_id))
    if not details:
        raise HTTPException(status_code=404, detail="Video not found")
    return VideoDetailResponse(**details)


@videos_router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get lightweight video status with current pipeline stage.

    Returns stage: script | audio | subtitles | media | compose | completed | failed
    """
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    stage = await _resolve_stage(db, video)

    return VideoStatusResponse(
        video_id=str(video.id),
        status=video.status,
        stage=stage,
        error=video.error,
        created_at=video.created_at.isoformat() if video.created_at else None,
        completed_at=video.completed_at.isoformat() if video.completed_at else None,
    )


@videos_router.get("/{video_id}/download")
async def download_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Download the rendered MP4 video file.

    Returns 400 if video is still processing, 404 if file is missing.
    """
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if video.status not in ("completed",):
        if video.status in ("pending", "queued", "running", "rendering"):
            raise HTTPException(
                status_code=400,
                detail=f"Video is still processing (status: {video.status})",
            )
        raise HTTPException(
            status_code=404,
            detail=f"Video generation failed: {video.error or 'unknown error'}",
        )

    if not video.file_path or not Path(video.file_path).exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk")

    filename = f"{video_id}.mp4"
    return FileResponse(
        path=video.file_path,
        media_type="video/mp4",
        filename=filename,
    )


@videos_router.get("", response_model=list[VideoListItem])
async def list_videos(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List videos, optionally filtered by status.

    Ordered by created_at DESC (newest first).
    """
    query = select(Video).order_by(Video.created_at.desc())
    if status is not None:
        query = query.where(Video.status == status)
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    videos = list(result.scalars().all())

    return [
        VideoListItem(
            id=str(v.id),
            script_id=str(v.script_id),
            status=v.status,
            file_path=v.file_path,
            file_size_bytes=v.file_size_bytes,
            duration_seconds=v.duration_seconds,
            error=v.error,
            created_at=v.created_at.isoformat() if v.created_at else None,
            completed_at=v.completed_at.isoformat() if v.completed_at else None,
        )
        for v in videos
    ]


@videos_router.get("/{video_id}/stream")
async def stream_video_status(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Stream video status updates via Server-Sent Events (SSE).

    Sends a status event whenever the pipeline stage changes.
    Stops streaming when stage reaches 'completed' or 'failed'.
    """
    # Verify video exists
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    async def event_generator():
        last_stage = None
        max_iterations = 600  # Max 10 minutes at 1s intervals
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Re-query video status in a new session
            async with db.__class__.__module__:  # Use fresh session
                pass

            # Use a fresh DB query for each iteration
            from app.db import async_session as session_factory
            async with session_factory() as stream_session:
                video_result = await stream_session.execute(
                    select(Video).where(Video.id == video_id)
                )
                current_video = video_result.scalar_one_or_none()

                if not current_video:
                    yield f"data: {json.dumps({'error': 'Video not found'})}\n\n"
                    break

                stage = await _resolve_stage(stream_session, current_video)

                if stage != last_stage:
                    status_data = {
                        "video_id": str(current_video.id),
                        "status": current_video.status,
                        "stage": stage,
                        "error": current_video.error,
                        "created_at": current_video.created_at.isoformat() if current_video.created_at else None,
                        "completed_at": current_video.completed_at.isoformat() if current_video.completed_at else None,
                    }
                    yield f"data: {json.dumps(status_data)}\n\n"
                    last_stage = stage

                    if stage in ("completed", "failed"):
                        break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
