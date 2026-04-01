"""Tests for the video REST API endpoints — Phase 8.

Tests validate API contract: route registration, Pydantic schema validation,
status resolution logic, and Celery task integration.
Follows project test patterns (mocks, no real HTTP calls).
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.videos import (
    VideoGenerateRequest,
    VideoStatusResponse,
    _resolve_stage,
    videos_router,
)
from app.main import app


# =============================================================================
# Test: Router Registration
# =============================================================================


class TestRouterRegistration:
    """Verify videos router is included in the FastAPI app."""

    def test_videos_router_prefix(self):
        """Router prefix is /api/videos."""
        assert videos_router.prefix == "/api/videos"

    def test_videos_router_in_app(self):
        """Videos router is registered in the app."""
        route_paths = [r.path for r in app.routes]
        assert "/api/videos/generate" in route_paths
        assert "/api/videos/{video_id}" in route_paths
        assert "/api/videos/{video_id}/status" in route_paths
        assert "/api/videos/{video_id}/download" in route_paths
        assert "/api/videos" in route_paths

    def test_videos_stream_endpoint_registered(self):
        """SSE streaming endpoint is registered."""
        route_paths = [r.path for r in app.routes]
        assert "/api/videos/{video_id}/stream" in route_paths


# =============================================================================
# Test: Request Schema Validation
# =============================================================================


class TestVideoGenerateRequest:
    """Pydantic schema validation for video generation requests."""

    def test_valid_request(self):
        """Valid request with prompt passes validation."""
        req = VideoGenerateRequest(prompt="Test topic")
        assert req.prompt == "Test topic"
        assert req.voice == "zh-CN-YunxiNeural"
        assert req.title == ""

    def test_valid_request_with_options(self):
        """Request with all fields passes validation."""
        req = VideoGenerateRequest(
            prompt="Test",
            title="My Video",
            voice="en-US-JennyNeural",
        )
        assert req.title == "My Video"
        assert req.voice == "en-US-JennyNeural"

    def test_empty_prompt_fails(self):
        """Empty prompt fails validation."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            VideoGenerateRequest(prompt="")

    def test_long_prompt_fails(self):
        """Prompt over 4000 chars fails validation."""
        with pytest.raises(Exception):
            VideoGenerateRequest(prompt="x" * 4001)


# =============================================================================
# Test: Status Resolution Logic
# =============================================================================


class TestStatusResolution:
    """Tests for pipeline stage resolution function."""

    def test_completed_status(self):
        """Completed video returns 'completed' stage."""
        mock_video = MagicMock()
        mock_video.status = "completed"
        mock_video.render_props = None

        mock_db = AsyncMock()
        # Run the async function
        import asyncio
        stage = asyncio.run(_resolve_stage(mock_db, mock_video))
        assert stage == "completed"

    def test_failed_status(self):
        """Failed video returns 'failed' stage."""
        mock_video = MagicMock()
        mock_video.status = "failed"
        mock_video.render_props = None

        mock_db = AsyncMock()
        import asyncio
        stage = asyncio.run(_resolve_stage(mock_db, mock_video))
        assert stage == "failed"

    def test_stage_from_render_props(self):
        """Stage is read from render_props when available."""
        mock_video = MagicMock()
        mock_video.status = "running"
        mock_video.render_props = {"stage": "audio"}

        mock_db = AsyncMock()
        import asyncio
        stage = asyncio.run(_resolve_stage(mock_db, mock_video))
        assert stage == "audio"

    def test_stage_compose_from_render_props(self):
        """Compose stage from render_props."""
        mock_video = MagicMock()
        mock_video.status = "rendering"
        mock_video.render_props = {"stage": "compose"}

        mock_db = AsyncMock()
        import asyncio
        stage = asyncio.run(_resolve_stage(mock_db, mock_video))
        assert stage == "compose"

    def test_stage_subtitles_from_render_props(self):
        """Subtitles stage from render_props."""
        mock_video = MagicMock()
        mock_video.status = "running"
        mock_video.render_props = {"stage": "subtitles"}

        mock_db = AsyncMock()
        import asyncio
        stage = asyncio.run(_resolve_stage(mock_db, mock_video))
        assert stage == "subtitles"


# =============================================================================
# Test: Video Status Response Schema
# =============================================================================


class TestVideoStatusResponse:
    """Verify VideoStatusResponse schema."""

    def test_response_fields(self):
        """Response has all required fields."""
        resp = VideoStatusResponse(
            video_id=str(uuid.uuid4()),
            status="running",
            stage="audio",
            error=None,
            created_at="2026-04-01T00:00:00",
            completed_at=None,
        )
        assert resp.status == "running"
        assert resp.stage == "audio"
        assert resp.error is None


# =============================================================================
# Test: Celery Task Integration
# =============================================================================


class TestCeleryTaskIntegration:
    """Verify pipeline task is properly registered."""

    def test_pipeline_task_is_celery_task(self):
        """Pipeline task is a Celery task."""
        from app.tasks.video_pipeline import generate_video_pipeline_task
        from celery import Task

        assert isinstance(generate_video_pipeline_task, Task)

    def test_pipeline_task_has_correct_name(self):
        """Pipeline task name matches routing config."""
        from app.tasks.video_pipeline import generate_video_pipeline_task

        assert generate_video_pipeline_task.name == "app.tasks.pipeline.generate_video"

    def test_tts_task_is_celery_task(self):
        """TTS task is a Celery task."""
        from app.tasks.tts_tasks import generate_audio_task
        from celery import Task

        assert isinstance(generate_audio_task, Task)

    def test_tts_task_has_correct_name(self):
        """TTS task name is correct."""
        from app.tasks.tts_tasks import generate_audio_task

        assert generate_audio_task.name == "app.tasks.tts.generate"

    def test_celery_app_has_pipeline_queue(self):
        """Celery app routes pipeline tasks to scripts queue."""
        from app.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert "app.tasks.pipeline.*" in routes
        assert routes["app.tasks.pipeline.*"]["queue"] == "scripts"


# =============================================================================
# Test: OrchestratorService
# =============================================================================


class TestOrchestratorService:
    """Verify OrchestratorService exists and is importable."""

    def test_orchestrator_importable(self):
        """OrchestratorService can be imported."""
        from app.services.orchestrator import OrchestratorService

        service = OrchestratorService()
        assert hasattr(service, "start_pipeline")
        assert hasattr(service, "get_video_with_details")

    def test_orchestrator_module_singleton(self):
        """Module-level singleton exists."""
        from app.services.orchestrator import orchestrator_service

        assert orchestrator_service is not None
