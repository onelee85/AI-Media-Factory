import pytest
from pathlib import Path

from app.config import settings
from app.celery_app import celery_app
from app.storage import StorageService
from app.ffmpeg_utils import check_ffmpeg, generate_test_clip
from app.models.project import Project
from app.models.task import Task


class TestSettings:
    def test_settings_load(self):
        assert settings.app_name == "AI-Media-Factory"
        assert settings.redis_url == "redis://localhost:6379/0"
        assert settings.database_url.startswith("postgresql+asyncpg://")
        assert settings.ffmpeg_binary == "ffmpeg"
        assert settings.storage_root == Path("./storage")


class TestCelery:
    def test_celery_app_exists(self):
        assert celery_app.main == "ai_media_factory"
        routes = celery_app.conf.task_routes
        assert "app.tasks.tts.*" in routes
        assert routes["app.tasks.tts.*"]["queue"] == "tts"


class TestModels:
    def test_models_importable(self):
        assert Project.__tablename__ == "projects"
        assert Task.__tablename__ == "tasks"


class TestStorage:
    def test_storage_service(self, tmp_path):
        service = StorageService(root=tmp_path)
        project_path = service.project_dir("test-project-123")
        assert project_path.exists()
        assert project_path.parent.name == "projects"


class TestFFmpeg:
    def test_ffmpeg_check(self):
        result = check_ffmpeg()
        assert result["available"] is True
        assert "version" in result

    def test_ffmpeg_generate_clip(self, tmp_path):
        output = tmp_path / "test_clip.mp4"
        result = generate_test_clip(output, duration=2)
        assert result.exists()
        assert result.stat().st_size > 1024


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, anyio_backend):
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ("healthy", "degraded")
            assert "checks" in data
            assert "redis" in data["checks"]
            assert "postgres" in data["checks"]
            assert "ffmpeg" in data["checks"]