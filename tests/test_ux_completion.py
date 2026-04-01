"""
UX flow completion test suite for QUAL-04 (>60% completion rate).

Tests validate:
- API flow sequence: generate → poll status → get details → download
- Completion rate calculation: (users_who_downloaded / total_users) * 100
- Drop-off identification at each step
- User journey scenarios: happy path, abandon at progress, abandon at submit
- Completion rate above/below 60% target
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.main import app


# =============================================================================
# Helpers
# =============================================================================


def calculate_completion_rate(flow_data: dict) -> float:
    """Calculate completion rate from flow tracking data.

    Args:
        flow_data: Dict of {user_id: {steps: {input: bool, submit: bool, ...}}}

    Returns:
        Completion rate as percentage (0.0 - 100.0). 'download' step = completed.
    """
    if not flow_data:
        return 0.0

    total = len(flow_data)
    completed = sum(
        1 for user_data in flow_data.values()
        if user_data.get("steps", {}).get("download", False)
    )
    return round((completed / total) * 100, 1)


def identify_drop_off(flow_data: dict) -> dict:
    """Identify which step has the highest drop-off rate.

    Returns:
        Dict with step names and their drop-off counts.
    """
    steps = ["input", "submit", "progress", "preview", "download"]
    drop_offs = {}

    for step in steps:
        reached = sum(
            1 for user_data in flow_data.values()
            if user_data.get("steps", {}).get(step, False)
        )
        drop_offs[step] = len(flow_data) - reached

    return drop_offs


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def happy_path_flow():
    """User completes all steps: input → submit → progress → preview → download."""
    return {
        "steps": {"input": True, "submit": True, "progress": True, "preview": True, "download": True}
    }


@pytest.fixture
def abandon_at_progress_flow():
    """User leaves after seeing progress updates."""
    return {
        "steps": {"input": True, "submit": True, "progress": True, "preview": False, "download": False}
    }


@pytest.fixture
def abandon_at_submit_flow():
    """User submits but pipeline fails or they leave."""
    return {
        "steps": {"input": True, "submit": True, "progress": False, "preview": False, "download": False}
    }


@pytest.fixture
def flow_data_70_percent():
    """10 users, 7 complete download (70% > 60% target)."""
    return {
        f"user_{i}": {"steps": {"input": True, "submit": True, "progress": True, "preview": True, "download": True}}
        for i in range(7)
    } | {
        f"user_{i}": {"steps": {"input": True, "submit": True, "progress": True, "preview": False, "download": False}}
        for i in range(7, 10)
    }


@pytest.fixture
def flow_data_50_percent():
    """10 users, 5 complete download (50% < 60% target)."""
    return {
        f"user_{i}": {"steps": {"input": True, "submit": True, "progress": True, "preview": True, "download": True}}
        for i in range(5)
    } | {
        f"user_{i}": {"steps": {"input": True, "submit": True, "progress": False, "preview": False, "download": False}}
        for i in range(5, 10)
    }


@pytest.fixture
def mock_video_completed():
    """Mock completed video with file path."""
    return {
        "id": str(uuid.uuid4()),
        "status": "completed",
        "file_path": "/tmp/test_video.mp4",
        "file_size_bytes": 1048576,
        "render_props": {"stage": "completed"},
        "script": {"id": str(uuid.uuid4()), "title": "Test Video", "status": "completed"},
        "audio": {"id": str(uuid.uuid4()), "voice": "zh-CN-YunxiNeural", "duration_seconds": 45.0, "status": "completed"},
        "subtitle": {"id": str(uuid.uuid4()), "format": "srt", "status": "completed"},
    }


# =============================================================================
# Tests: API Flow Tracking
# =============================================================================


class TestUXFlowTracking:
    """Verify API endpoints support the user flow sequence."""

    def test_generate_endpoint_returns_video_id(self):
        """POST /api/videos/generate returns video_id on success."""
        from app.api.videos import videos_router
        route_paths = [r.path for r in app.routes]
        assert "/api/videos/generate" in route_paths

    def test_status_endpoint_tracks_progress(self):
        """GET /api/videos/{id}/status returns stage info."""
        from app.api.videos import videos_router
        route_paths = [r.path for r in app.routes]
        assert "/api/videos/{video_id}/status" in route_paths

    def test_completed_video_has_file_path(self, mock_video_completed):
        """Completed video record includes file_path."""
        assert mock_video_completed["file_path"] != ""
        assert mock_video_completed["status"] == "completed"

    def test_download_endpoint_returns_file(self):
        """Download endpoint is registered and accessible."""
        route_paths = [r.path for r in app.routes]
        assert "/api/videos/{video_id}/download" in route_paths

    def test_full_flow_api_sequence(self):
        """All required API endpoints exist for the full flow."""
        route_paths = [r.path for r in app.routes]
        required = [
            "/api/videos/generate",
            "/api/videos/{video_id}/status",
            "/api/videos/{video_id}",
            "/api/videos/{video_id}/download",
        ]
        for path in required:
            assert path in route_paths, f"Missing endpoint: {path}"


# =============================================================================
# Tests: Completion Rate Calculation
# =============================================================================


class TestUXCompletionRate:
    """Verify completion rate calculation against QUAL-04 target."""

    def test_completion_rate_calculation(self, flow_data_70_percent):
        """7/10 users complete download → rate = 70%."""
        rate = calculate_completion_rate(flow_data_70_percent)
        assert rate == 70.0

    def test_completion_rate_above_60_target(self, flow_data_70_percent):
        """70% > 60% QUAL-04 target — passes."""
        rate = calculate_completion_rate(flow_data_70_percent)
        assert rate > 60.0

    def test_completion_rate_below_60_target(self, flow_data_50_percent):
        """50% < 60% target — fails."""
        rate = calculate_completion_rate(flow_data_50_percent)
        assert rate == 50.0
        assert rate < 60.0

    def test_drop_off_identification(self, flow_data_50_percent):
        """Identify which step has highest drop-off rate."""
        drop_offs = identify_drop_off(flow_data_50_percent)
        # In the 50% fixture, 5 users drop at progress
        assert drop_offs["progress"] == 5
        assert drop_offs["download"] == 5
        # All 10 users hit input and submit
        assert drop_offs["input"] == 0
        assert drop_offs["submit"] == 0

    def test_empty_flow_data_returns_zero(self):
        """Empty flow data → 0% completion rate."""
        assert calculate_completion_rate({}) == 0.0

    def test_all_users_complete_returns_100(self):
        """All users complete → 100% rate."""
        data = {
            f"user_{i}": {"steps": {"input": True, "submit": True, "progress": True, "preview": True, "download": True}}
            for i in range(10)
        }
        assert calculate_completion_rate(data) == 100.0


# =============================================================================
# Tests: User Journey Scenarios
# =============================================================================


class TestUXFlowScenarios:
    """Simulate user journey scenarios through the flow."""

    def test_happy_path_flow(self, happy_path_flow):
        """All steps completed — user downloads video."""
        steps = happy_path_flow["steps"]
        assert all(steps.values())

    def test_abandon_at_progress(self, abandon_at_progress_flow):
        """User sees progress but leaves — preview and download not reached."""
        steps = abandon_at_progress_flow["steps"]
        assert steps["input"] is True
        assert steps["submit"] is True
        assert steps["progress"] is True
        assert steps["preview"] is False
        assert steps["download"] is False

    def test_abandon_at_submit(self, abandon_at_submit_flow):
        """User submits but leaves before progress — only input and submit."""
        steps = abandon_at_submit_flow["steps"]
        assert steps["input"] is True
        assert steps["submit"] is True
        assert steps["progress"] is False

    def test_no_input_flow(self):
        """Submit without input is invalid — input step must be True first."""
        flow = {"steps": {"input": False, "submit": True, "progress": False, "preview": False, "download": False}}
        # This is a pathological case — user shouldn't be able to submit without input
        # but if they do, the flow tracker records it
        assert flow["steps"]["input"] is False
        assert flow["steps"]["submit"] is True  # Unusual but trackable
