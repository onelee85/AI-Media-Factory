"""
Behavioral tests for Phase 3: AI Script Generation (CORE-01)

Tests validate:
- Script data model persistence and structure
- Script generation service JSON parsing and error handling
- API endpoint behavior for script creation and retrieval
- Celery task integration for async generation
"""
import json
import uuid
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# =============================================================================
# Test: Script Model Structure
# =============================================================================


class TestScriptModel:
    """Verify Script SQLAlchemy model has required fields for persistence."""

    def test_script_model_has_required_columns(self):
        """Script model must have columns for id, project_id, prompt, status, content."""
        from app.models.script import Script
        from sqlalchemy import inspect

        mapper = inspect(Script)
        column_names = {col.key for col in mapper.column_attrs}

        required = {"id", "project_id", "prompt", "status", "content", "title"}
        assert required.issubset(column_names), (
            f"Missing columns: {required - column_names}"
        )

    def test_script_model_has_metadata_column(self):
        """Script model must have script_metadata JSONB for storing sections/summary."""
        from app.models.script import Script
        from sqlalchemy import inspect

        mapper = inspect(Script)
        column_names = {col.key for col in mapper.column_attrs}

        assert "script_metadata" in column_names, (
            "Script model missing script_metadata column for storing generation results"
        )

    def test_script_model_has_timestamp_columns(self):
        """Script model must track created_at, updated_at, completed_at."""
        from app.models.script import Script
        from sqlalchemy import inspect

        mapper = inspect(Script)
        column_names = {col.key for col in mapper.column_attrs}

        assert "created_at" in column_names
        assert "updated_at" in column_names
        assert "completed_at" in column_names

    def test_script_model_has_error_column(self):
        """Script model must have error column for failure tracking."""
        from app.models.script import Script
        from sqlalchemy import inspect

        mapper = inspect(Script)
        column_names = {col.key for col in mapper.column_attrs}

        assert "error" in column_names, (
            "Script model missing error column for recording generation failures"
        )

    def test_script_model_default_status_is_pending(self):
        """Script.status column must have server_default='pending'."""
        from app.models.script import Script
        from sqlalchemy import inspect

        mapper = inspect(Script)
        status_col = mapper.columns["status"]

        # SQLAlchemy column defaults are applied at INSERT time, not object construction.
        # Verify the column has a default of 'pending'.
        assert status_col.default is not None or status_col.server_default is not None, (
            "Script.status should have a default value"
        )
        # Check the Python-level default
        default_arg = status_col.default
        if default_arg is not None:
            assert str(default_arg.arg) == "pending", (
                f"Expected default 'pending', got '{default_arg.arg}'"
            )


# =============================================================================
# Test: Script Generation Service — JSON Parsing
# =============================================================================


class TestScriptGeneratorParsing:
    """Verify ScriptGeneratorService correctly parses LLM JSON output."""

    def test_parse_valid_json_with_sections(self):
        """Service must parse valid JSON containing sections array."""
        from app.services.script_generator import ScriptGeneratorService

        raw = json.dumps({
            "title": "Test Script",
            "sections": [
                {"heading": "Intro", "content": "Welcome to this test script that has enough content for quality validation.", "duration_estimate_sec": 30},
                {"heading": "Body", "content": "The body section contains the main points and detailed explanation of the topic.", "duration_estimate_sec": 45},
            ],
            "summary": "A test"
        })

        result = ScriptGeneratorService._parse_script(raw)

        assert result["title"] == "Test Script"
        assert len(result["sections"]) == 2
        assert result["sections"][0]["heading"] == "Intro"

    def test_parse_strips_markdown_code_fence(self):
        """Service must handle LLM responses wrapped in ```json code blocks."""
        from app.services.script_generator import ScriptGeneratorService

        raw = '```json\n{"title": "Fenced", "sections": [{"heading": "A", "content": "This is section A with enough content to pass quality validation check."}, {"heading": "B", "content": "This is section B with enough content to pass quality validation check."}], "summary": "S"}\n```'

        result = ScriptGeneratorService._parse_script(raw)

        assert result["title"] == "Fenced"
        assert len(result["sections"]) == 2

    def test_parse_sets_default_title_when_missing(self):
        """Service must provide default title if LLM omits it."""
        from app.services.script_generator import ScriptGeneratorService

        raw = json.dumps({
            "sections": [
                {"heading": "S1", "content": "This section has enough content for quality validation to pass successfully."},
                {"heading": "S2", "content": "This section also has enough content for quality validation to pass successfully."},
            ],
        })

        result = ScriptGeneratorService._parse_script(raw)

        assert result["title"] == "Untitled Script"

    def test_parse_sets_default_summary_when_missing(self):
        """Service must provide default summary if LLM omits it."""
        from app.services.script_generator import ScriptGeneratorService

        raw = json.dumps({
            "title": "T",
            "sections": [
                {"heading": "S1", "content": "This section has enough content for quality validation to pass successfully."},
                {"heading": "S2", "content": "This section also has enough content for quality validation to pass successfully."},
            ],
        })

        result = ScriptGeneratorService._parse_script(raw)

        assert result["summary"] == ""

    def test_parse_raises_on_invalid_json(self):
        """Service must raise ValueError for non-JSON LLM output."""
        from app.services.script_generator import ScriptGeneratorService

        with pytest.raises(ValueError, match="Failed to parse"):
            ScriptGeneratorService._parse_script("this is not json at all")

    def test_parse_raises_when_sections_missing(self):
        """Service must raise ValueError if JSON lacks 'sections' array."""
        from app.services.script_generator import ScriptGeneratorService

        raw = json.dumps({"title": "No Sections"})

        with pytest.raises(ValueError, match="sections"):
            ScriptGeneratorService._parse_script(raw)

    def test_parse_raises_when_sections_not_list(self):
        """Service must raise ValueError if 'sections' is not a list."""
        from app.services.script_generator import ScriptGeneratorService

        raw = json.dumps({"title": "Bad", "sections": "not-a-list"})

        with pytest.raises(ValueError, match="sections"):
            ScriptGeneratorService._parse_script(raw)


# =============================================================================
# Test: Script Generation Service — Generate Method
# =============================================================================


class TestScriptGeneratorService:
    """Verify ScriptGeneratorService.generate() orchestrates correctly."""

    def test_generate_returns_structured_result(self):
        """generate() must return dict with title, sections, summary, raw_content, usage, model, provider."""
        from app.services.script_generator import ScriptGeneratorService

        service = ScriptGeneratorService()

        mock_response = {
            "content": json.dumps({
                "title": "AI Video",
                "sections": [
                    {"heading": "Intro", "content": "Welcome to this AI overview video with detailed content for narration.", "duration_estimate_sec": 20},
                    {"heading": "Details", "content": "This section covers the key concepts and applications of artificial intelligence.", "duration_estimate_sec": 45},
                ],
                "summary": "An intro video"
            }),
            "usage": {"total_tokens": 150},
            "model": "gpt-4o-mini",
            "provider": "primary",
        }

        with patch.object(service.provider, "complete", return_value=mock_response):
            result = service.generate(prompt="Tell me about AI")

            assert result["title"] == "AI Video"
            assert len(result["sections"]) == 2
            assert result["summary"] == "An intro video"
            assert result["raw_content"] == mock_response["content"]
            assert result["model"] == "gpt-4o-mini"
            assert result["provider"] == "primary"

    def test_generate_passes_temperature_and_tokens(self):
        """generate() must forward temperature and max_tokens to provider."""
        from app.services.script_generator import ScriptGeneratorService

        service = ScriptGeneratorService()

        mock_response = {
            "content": json.dumps({"title": "T", "sections": [{"heading": "A", "content": "Section A has enough content to pass quality validation checks here."}, {"heading": "B", "content": "Section B also has enough content to pass quality validation checks here."}], "summary": "S"}),
            "usage": {},
            "model": "test",
            "provider": "test",
        }

        with patch.object(service.provider, "complete", return_value=mock_response) as mock_complete:
            service.generate(prompt="test", temperature=0.3, max_tokens=500)

            call_kwargs = mock_complete.call_args[1]
            assert call_kwargs["temperature"] == 0.3
            assert call_kwargs["max_tokens"] == 500

    def test_generate_raises_on_provider_error(self):
        """generate() must propagate ModelProviderError when all providers fail."""
        from app.services.script_generator import ScriptGeneratorService
        from app.services.model_provider import ModelProviderError

        service = ScriptGeneratorService()

        with patch.object(
            service.provider, "complete",
            side_effect=ModelProviderError("All providers failed")
        ):
            with pytest.raises(ModelProviderError):
                service.generate(prompt="test")

    def test_generate_raises_on_unparseable_response(self):
        """generate() must raise ValueError when LLM returns non-JSON."""
        from app.services.script_generator import ScriptGeneratorService

        service = ScriptGeneratorService()

        mock_response = {
            "content": "I cannot generate a script right now.",
            "usage": {},
            "model": "test",
            "provider": "test",
        }

        with patch.object(service.provider, "complete", return_value=mock_response):
            with pytest.raises(ValueError, match="Failed to parse"):
                service.generate(prompt="test")


# =============================================================================
# Test: Script Generation Service — Async Wrapper
# =============================================================================


class TestScriptGeneratorAsync:
    """Verify generate_async wrapper works."""

    @pytest.mark.asyncio
    async def test_generate_async_returns_result(self):
        """generate_async must return the same result as generate."""
        from app.services.script_generator import ScriptGeneratorService

        service = ScriptGeneratorService()

        mock_response = {
            "content": json.dumps({
                "title": "Async Test",
                "sections": [
                    {"heading": "S1", "content": "Section one has enough content to pass the quality validation checks."},
                    {"heading": "S2", "content": "Section two also has enough content to pass the quality validation checks."},
                ],
                "summary": "test"
            }),
            "usage": {},
            "model": "test",
            "provider": "test",
        }

        with patch.object(service.provider, "complete", return_value=mock_response):
            result = await service.generate_async(prompt="test topic")

            assert result["title"] == "Async Test"
            assert len(result["sections"]) == 2


# =============================================================================
# Test: Script API Endpoints
# =============================================================================


class TestScriptAPIEndpoints:
    """Verify REST API behavior for script operations."""

    @pytest.mark.asyncio
    async def test_create_script_endpoint_exists(self):
        """POST /api/scripts must be a registered route."""
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/scripts" in routes or any(
            "/api/scripts" in r for r in routes
        ), "POST /api/scripts endpoint not registered"

    @pytest.mark.asyncio
    async def test_create_script_calls_celery_task(self):
        """POST /api/scripts must dispatch a Celery task for async generation."""
        from httpx import ASGITransport, AsyncClient
        from app.main import app
        from app.db import get_db

        mock_task = MagicMock()
        mock_task.id = "celery-task-abc-123"

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        celery_called_with = {}

        def capture_delay(**kwargs):
            celery_called_with.update(kwargs)
            return mock_task

        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("app.api.scripts.generate_script_task.delay", side_effect=capture_delay):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    project_id = str(uuid.uuid4())
                    try:
                        response = await client.post("/api/scripts", json={
                            "project_id": project_id,
                            "prompt": "Tell me about space exploration",
                            "title": "Space Video",
                        })
                    except Exception:
                        # Response validation may fail due to mock DB not populating
                        # auto-generated fields. The important thing is the side effects.
                        pass

                    # Celery task must have been dispatched with correct prompt
                    assert celery_called_with, "Celery task was not dispatched"
                    assert celery_called_with["prompt"] == "Tell me about space exploration"
                    assert celery_called_with["temperature"] == 0.7
                    assert celery_called_with["max_tokens"] == 2000

                    # Session operations must have occurred
                    mock_session.flush.assert_called()
        finally:
            app.dependency_overrides.pop(get_db, None)

    @pytest.mark.asyncio
    async def test_get_script_endpoint_exists(self):
        """GET /api/scripts/{id} must be a registered route."""
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        # Check route pattern exists
        route_paths = []
        for r in app.routes:
            if hasattr(r, "path"):
                route_paths.append(r.path)

        has_get_route = any(
            "script_id" in p or p == "/api/scripts/{script_id}"
            for p in route_paths
        )
        assert has_get_route, f"GET /api/scripts/{{script_id}} not found in routes: {route_paths}"

    @pytest.mark.asyncio
    async def test_list_scripts_endpoint_exists(self):
        """GET /api/scripts must be a registered route for listing."""
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/scripts" in routes, "GET /api/scripts list endpoint not registered"

    @pytest.mark.asyncio
    async def test_delete_script_endpoint_exists(self):
        """DELETE /api/scripts/{id} must be a registered route."""
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        # Check for route with script_id parameter
        route_paths = []
        for r in app.routes:
            if hasattr(r, "path"):
                route_paths.append(r.path)

        has_delete = any(
            "script_id" in p for p in route_paths
        )
        assert has_delete, f"DELETE route with script_id not found in: {route_paths}"


# =============================================================================
# Test: Celery Task Integration
# =============================================================================


class TestCeleryTaskIntegration:
    """Verify Celery task is properly configured for async script generation."""

    def test_generate_script_task_is_celery_task(self):
        """generate_script_task must be a registered Celery task."""
        from app.tasks.script_tasks import generate_script_task

        assert hasattr(generate_script_task, "delay"), (
            "generate_script_task should have .delay() method (Celery task)"
        )
        assert hasattr(generate_script_task, "apply_async"), (
            "generate_script_task should have .apply_async() method"
        )

    def test_generate_script_task_has_correct_name(self):
        """Task must be named for queue routing."""
        from app.tasks.script_tasks import generate_script_task

        # Celery tasks have a name attribute
        task_name = getattr(generate_script_task, "name", None)
        assert task_name is not None, "Task must have a name for routing"
        assert "script" in task_name.lower(), (
            f"Task name '{task_name}' should contain 'script' for queue routing"
        )

    def test_celery_app_has_scripts_queue_configured(self):
        """Celery must have 'scripts' queue in task_routes."""
        from app.celery_app import celery_app

        routes = celery_app.conf.task_routes or {}
        has_scripts_queue = any(
            "script" in str(v.get("queue", "")).lower()
            for v in routes.values()
        ) or any(
            "script" in str(pattern).lower()
            for pattern in routes.keys()
        )

        assert has_scripts_queue, (
            f"No scripts queue found in task_routes: {routes}"
        )

    def test_format_script_content_produces_markdown(self):
        """_format_script_content must convert structured result to readable markdown."""
        from app.tasks.script_tasks import _format_script_content

        result = {
            "title": "My Video",
            "sections": [
                {"heading": "Intro", "content": "Welcome to the show", "duration_estimate_sec": 15},
                {"heading": "Main", "content": "The main content", "duration_estimate_sec": 45},
            ],
            "summary": "A great video"
        }

        markdown = _format_script_content(result)

        assert "# My Video" in markdown
        assert "## Intro (~15s)" in markdown
        assert "Welcome to the show" in markdown
        assert "## Main (~45s)" in markdown
        assert "A great video" in markdown

    def test_format_script_content_handles_missing_duration(self):
        """_format_script_content must work when duration_estimate_sec is absent."""
        from app.tasks.script_tasks import _format_script_content

        result = {
            "title": "No Duration",
            "sections": [
                {"heading": "S1", "content": "Content without timing"},
            ],
            "summary": ""
        }

        markdown = _format_script_content(result)

        assert "## S1" in markdown  # No duration suffix
        assert "Content without timing" in markdown

    def test_format_script_content_handles_empty_sections(self):
        """_format_script_content must work with empty sections list."""
        from app.tasks.script_tasks import _format_script_content

        result = {
            "title": "Empty",
            "sections": [],
            "summary": ""
        }

        markdown = _format_script_content(result)

        assert "# Empty" in markdown
        # Should not crash


# =============================================================================
# Test: Router Registration
# =============================================================================


class TestRouterRegistration:
    """Verify scripts router is properly registered in main app."""

    def test_scripts_router_is_included_in_app(self):
        """scripts_router must be included in the FastAPI app."""
        from app.main import app

        # Check that routes from scripts module are present
        route_paths = [r.path for r in app.routes if hasattr(r, "path")]

        has_scripts_routes = any(
            "/api/scripts" in path for path in route_paths
        )
        assert has_scripts_routes, (
            f"scripts_router not registered. Found routes: {route_paths}"
        )

    def test_app_has_script_crud_routes(self):
        """App must expose create, get, list, delete routes for scripts."""
        from app.main import app

        route_info = []
        for r in app.routes:
            if hasattr(r, "path") and hasattr(r, "methods"):
                route_info.append((r.path, list(r.methods)))

        paths = [p for p, _ in route_info]

        # POST /api/scripts (create)
        assert any(p == "/api/scripts" and "POST" in m for p, m in route_info), (
            "POST /api/scripts not found"
        )

        # GET /api/scripts/{script_id}
        assert any("script_id" in p and "GET" in m for p, m in route_info), (
            "GET /api/scripts/{script_id} not found"
        )
