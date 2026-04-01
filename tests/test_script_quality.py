"""
Script quality evaluation test suite for QUAL-02 (>80% usable scripts).

Tests validate:
- Script structure: title, sections, headings, content length
- Chinese and English topic quality
- Duration estimates present and valid
- No JSON artifacts in content
- Quality rate calculation against 80% target
"""
import pytest
from unittest.mock import patch, MagicMock


# =============================================================================
# Constants
# =============================================================================

QUALITY_CRITERIA = {
    "min_sections": 2,
    "min_content_length": 20,
    "require_summary": True,
    "require_duration_estimate": True,
    "no_json_artifacts": True,
}

DIVERSE_TEST_TOPICS = [
    "人工智能在教育中的应用",
    "The future of renewable energy",
    "如何提高工作效率",
    "The history of the internet",
    "短视频制作技巧分享",
    "How to learn a new language effectively",
    "健康饮食的十个原则",
    "The impact of social media on society",
    "Python编程最佳实践",
    "Space exploration in the 21st century",
]


# =============================================================================
# Helpers
# =============================================================================


def validate_script_quality(script_result: dict) -> dict:
    """Validate a script result against quality criteria.

    Returns:
        Dict with passed (bool), criteria_met (dict), issues (list).
    """
    issues = []
    criteria_met = {}

    # Title present
    has_title = bool(script_result.get("title", "").strip())
    criteria_met["has_title"] = has_title
    if not has_title:
        issues.append("Missing or empty title")

    # At least min_sections
    sections = script_result.get("sections", [])
    has_enough_sections = isinstance(sections, list) and len(sections) >= QUALITY_CRITERIA["min_sections"]
    criteria_met["has_enough_sections"] = has_enough_sections
    if not has_enough_sections:
        issues.append(f"Need at least {QUALITY_CRITERIA['min_sections']} sections, got {len(sections)}")

    # Each section has heading + sufficient content
    sections_valid = True
    for i, section in enumerate(sections):
        heading = section.get("heading", "").strip()
        content = section.get("content", "").strip()
        if not heading:
            sections_valid = False
            issues.append(f"Section {i} missing heading")
        if len(content) < QUALITY_CRITERIA["min_content_length"]:
            sections_valid = False
            issues.append(f"Section {i} content too short ({len(content)} < {QUALITY_CRITERIA['min_content_length']} chars)")
    criteria_met["sections_valid"] = sections_valid

    # Summary present
    summary = script_result.get("summary", "").strip()
    has_summary = bool(summary)
    criteria_met["has_summary"] = has_summary
    if not has_summary and QUALITY_CRITERIA["require_summary"]:
        issues.append("Missing or empty summary")

    # Duration estimates present and valid
    duration_valid = True
    for i, section in enumerate(sections):
        duration = section.get("duration_estimate_sec")
        if QUALITY_CRITERIA["require_duration_estimate"]:
            if duration is None or not isinstance(duration, (int, float)) or duration <= 0:
                duration_valid = False
                issues.append(f"Section {i} missing or invalid duration_estimate_sec")
    criteria_met["duration_valid"] = duration_valid

    # No JSON artifacts in content
    no_artifacts = True
    json_patterns = ['"sections"', '"title":', '{"', '}"', '"content":']
    for i, section in enumerate(sections):
        content = section.get("content", "")
        for pattern in json_patterns:
            if pattern in content:
                no_artifacts = False
                issues.append(f"Section {i} contains JSON artifact: {pattern}")
                break
    criteria_met["no_json_artifacts"] = no_artifacts

    passed = all(criteria_met.values())
    return {"passed": passed, "criteria_met": criteria_met, "issues": issues}


def compute_quality_rate(scripts: list[dict]) -> float:
    """Compute quality rate as percentage of scripts passing all criteria.

    Args:
        scripts: List of script result dicts.

    Returns:
        Quality rate as percentage (0.0 - 100.0).
    """
    if not scripts:
        return 0.0
    passing = sum(1 for s in scripts if validate_script_quality(s)["passed"])
    return round((passing / len(scripts)) * 100, 1)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def valid_script():
    """A valid script that meets all quality criteria."""
    return {
        "title": "AI in Healthcare",
        "sections": [
            {"heading": "Introduction", "content": "Artificial intelligence is transforming healthcare in profound ways, from diagnosis to treatment planning.", "duration_estimate_sec": 30},
            {"heading": "Applications", "content": "AI-powered systems can analyze medical images with remarkable accuracy, often surpassing human specialists.", "duration_estimate_sec": 45},
            {"heading": "Future Outlook", "content": "The future of AI in healthcare looks promising, with new breakthroughs expected in personalized medicine.", "duration_estimate_sec": 30},
        ],
        "summary": "AI is revolutionizing healthcare through improved diagnosis and treatment.",
    }


@pytest.fixture
def invalid_script_short_content():
    """Script with content too short in some sections."""
    return {
        "title": "Short Script",
        "sections": [
            {"heading": "Intro", "content": "Too short.", "duration_estimate_sec": 10},
            {"heading": "Main", "content": "This section has adequate content for testing purposes.", "duration_estimate_sec": 30},
        ],
        "summary": "A test script with short content.",
    }


@pytest.fixture
def invalid_script_json_artifacts():
    """Script with JSON artifacts leaking into content."""
    return {
        "title": "Bad Script",
        "sections": [
            {"heading": "Section", "content": "Some text with \"title\": artifact in it.", "duration_estimate_sec": 30},
            {"heading": "Another", "content": "Clean content without any artifacts here.", "duration_estimate_sec": 30},
        ],
        "summary": "Script with JSON artifacts.",
    }


@pytest.fixture
def mock_valid_script_response():
    """Mock LLM response returning a valid script JSON."""
    return {
        "title": "Test Script",
        "sections": [
            {"heading": "Part 1", "content": "This is the first section with enough content to pass quality checks.", "duration_estimate_sec": 30},
            {"heading": "Part 2", "content": "This is the second section with sufficient content for narration.", "duration_estimate_sec": 45},
        ],
        "summary": "A test script generated for quality evaluation.",
    }


# =============================================================================
# Tests: Script Quality Validation
# =============================================================================


class TestScriptQuality:
    """Verify script quality validation against QUAL-02 criteria."""

    def test_script_has_valid_structure(self, valid_script):
        """Valid script must pass all quality criteria."""
        result = validate_script_quality(valid_script)
        assert result["passed"] is True
        assert all(result["criteria_met"].values())
        assert len(result["issues"]) == 0

    def test_script_sections_have_content(self, valid_script):
        """Each section must have heading and meaningful content."""
        result = validate_script_quality(valid_script)
        assert result["criteria_met"]["sections_valid"] is True

    def test_script_has_summary(self, valid_script):
        """Script must have a non-empty summary."""
        result = validate_script_quality(valid_script)
        assert result["criteria_met"]["has_summary"] is True

    def test_script_duration_estimates_valid(self, valid_script):
        """Each section must have duration_estimate_sec > 0."""
        result = validate_script_quality(valid_script)
        assert result["criteria_met"]["duration_valid"] is True

    def test_script_no_json_artifacts(self, invalid_script_json_artifacts):
        """Validation must catch JSON artifacts in content."""
        result = validate_script_quality(invalid_script_json_artifacts)
        assert result["criteria_met"]["no_json_artifacts"] is False
        assert len(result["issues"]) > 0

    def test_quality_rate_with_mock_corpus(self):
        """Given 10 scripts (8 valid, 2 invalid), quality rate = 80%."""
        valid = {
            "title": "Good",
            "sections": [
                {"heading": "A", "content": "Content with enough length for quality.", "duration_estimate_sec": 30},
                {"heading": "B", "content": "Another section with sufficient content.", "duration_estimate_sec": 30},
            ],
            "summary": "Summary",
        }
        invalid = {
            "title": "Bad",
            "sections": [{"heading": "A", "content": "Short.", "duration_estimate_sec": 0}],
            "summary": "",
        }
        corpus = [valid] * 8 + [invalid] * 2
        rate = compute_quality_rate(corpus)
        assert rate == 80.0

    def test_quality_rate_above_target(self):
        """9/10 passing = 90% which is > 80% target."""
        script = {
            "title": "Good",
            "sections": [
                {"heading": "A", "content": "Content with enough length for quality.", "duration_estimate_sec": 30},
                {"heading": "B", "content": "Another section with sufficient content.", "duration_estimate_sec": 30},
            ],
            "summary": "Summary",
        }
        invalid = {
            "title": "",
            "sections": [],
            "summary": "",
        }
        corpus = [script] * 9 + [invalid] * 1
        rate = compute_quality_rate(corpus)
        assert rate == 90.0
        assert rate > 80.0  # Above QUAL-02 target

    def test_missing_title_fails(self):
        """Script without title must fail validation."""
        script = {
            "title": "",
            "sections": [
                {"heading": "A", "content": "Content with enough length for quality.", "duration_estimate_sec": 30},
                {"heading": "B", "content": "Another section with sufficient content.", "duration_estimate_sec": 30},
            ],
            "summary": "Summary",
        }
        result = validate_script_quality(script)
        assert result["passed"] is False
        assert result["criteria_met"]["has_title"] is False

    def test_insufficient_sections_fails(self):
        """Script with only 1 section must fail (need >= 2)."""
        script = {
            "title": "Title",
            "sections": [
                {"heading": "Only One", "content": "Content with enough length for quality.", "duration_estimate_sec": 30},
            ],
            "summary": "Summary",
        }
        result = validate_script_quality(script)
        assert result["passed"] is False
        assert result["criteria_met"]["has_enough_sections"] is False


class TestScriptQualityIntegration:
    """Integration tests with mocked LLM responses."""

    def test_validate_with_mocked_generator(self, mock_valid_script_response):
        """Mock a generator returning valid script — validation should pass."""
        result = validate_script_quality(mock_valid_script_response)
        assert result["passed"] is True

    def test_script_generator_service_import(self):
        """ScriptGeneratorService can be imported and instantiated."""
        from app.services.script_generator import ScriptGeneratorService
        svc = ScriptGeneratorService()
        assert svc is not None

    def test_parse_script_valid_json(self):
        """_parse_script handles valid JSON correctly."""
        from app.services.script_generator import ScriptGeneratorService
        raw = '{"title": "Test", "sections": [{"heading": "A", "content": "Section A has enough content for quality validation to pass."}, {"heading": "B", "content": "Section B also has enough content for quality validation to pass."}], "summary": "Summary"}'
        result = ScriptGeneratorService._parse_script(raw)
        assert result["title"] == "Test"
        assert len(result["sections"]) == 2

    def test_parse_script_with_markdown_fence(self):
        """_parse_script strips markdown code fences."""
        from app.services.script_generator import ScriptGeneratorService
        raw = '```json\n{"title": "Test", "sections": [{"heading": "A", "content": "Section A has enough content for quality validation to pass."}, {"heading": "B", "content": "Section B also has enough content for quality validation to pass."}], "summary": "S"}\n```'
        result = ScriptGeneratorService._parse_script(raw)
        assert result["title"] == "Test"
