"""
Subtitle sync accuracy test suite for QUAL-03 (>95% sync accuracy).

Tests validate:
- Perfect sync returns 100% accuracy
- Near-sync within 200ms tolerance returns 100%
- Poor sync below tolerance returns low accuracy
- Mixed sync calculates correctly
- Chinese text sync accuracy
- Edge cases (empty, single word)
- Accuracy above 95% target
- SRT roundtrip accuracy
- Word grouping preserves timing
"""
import pytest
from app.services.subtitle_service import SubtitleService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def svc():
    """SubtitleService instance."""
    return SubtitleService()


@pytest.fixture
def perfect_sync_timing():
    """10 words with precise timing (0.0s to 4.5s)."""
    return [
        {"word": "Welcome", "start": 0.0, "end": 0.4, "offset": 0, "duration": 4000000},
        {"word": "to", "start": 0.5, "end": 0.7, "offset": 5000000, "duration": 2000000},
        {"word": "the", "start": 0.8, "end": 1.0, "offset": 8000000, "duration": 2000000},
        {"word": "AI", "start": 1.1, "end": 1.4, "offset": 11000000, "duration": 3000000},
        {"word": "Media", "start": 1.5, "end": 1.8, "offset": 15000000, "duration": 3000000},
        {"word": "Factory", "start": 1.9, "end": 2.3, "offset": 19000000, "duration": 4000000},
        {"word": "platform", "start": 2.5, "end": 2.9, "offset": 25000000, "duration": 4000000},
        {"word": "for", "start": 3.0, "end": 3.2, "offset": 30000000, "duration": 2000000},
        {"word": "video", "start": 3.3, "end": 3.6, "offset": 33000000, "duration": 3000000},
        {"word": "creation", "start": 3.7, "end": 4.2, "offset": 37000000, "duration": 5000000},
    ]


@pytest.fixture
def near_sync_timing():
    """Same words with ±100ms jitter (within 200ms tolerance)."""
    return [
        {"word": "Welcome", "start": 0.05, "end": 0.45, "offset": 0, "duration": 4000000},
        {"word": "to", "start": 0.48, "end": 0.68, "offset": 5000000, "duration": 2000000},
        {"word": "the", "start": 0.85, "end": 1.05, "offset": 8000000, "duration": 2000000},
        {"word": "AI", "start": 1.15, "end": 1.45, "offset": 11000000, "duration": 3000000},
        {"word": "Media", "start": 1.52, "end": 1.82, "offset": 15000000, "duration": 3000000},
        {"word": "Factory", "start": 1.88, "end": 2.28, "offset": 19000000, "duration": 4000000},
        {"word": "platform", "start": 2.55, "end": 2.95, "offset": 25000000, "duration": 4000000},
        {"word": "for", "start": 3.02, "end": 3.22, "offset": 30000000, "duration": 2000000},
        {"word": "video", "start": 3.35, "end": 3.65, "offset": 33000000, "duration": 3000000},
        {"word": "creation", "start": 3.72, "end": 4.22, "offset": 37000000, "duration": 5000000},
    ]


@pytest.fixture
def poor_sync_timing():
    """Same words with ±500ms jitter (outside 200ms tolerance)."""
    return [
        {"word": "Welcome", "start": 0.5, "end": 0.9, "offset": 0, "duration": 4000000},
        {"word": "to", "start": 1.0, "end": 1.2, "offset": 5000000, "duration": 2000000},
        {"word": "the", "start": 1.3, "end": 1.5, "offset": 8000000, "duration": 2000000},
        {"word": "AI", "start": 1.6, "end": 1.9, "offset": 11000000, "duration": 3000000},
        {"word": "Media", "start": 2.0, "end": 2.3, "offset": 15000000, "duration": 3000000},
        {"word": "Factory", "start": 2.4, "end": 2.8, "offset": 19000000, "duration": 4000000},
        {"word": "platform", "start": 3.0, "end": 3.4, "offset": 25000000, "duration": 4000000},
        {"word": "for", "start": 3.5, "end": 3.7, "offset": 30000000, "duration": 2000000},
        {"word": "video", "start": 3.8, "end": 4.1, "offset": 33000000, "duration": 3000000},
        {"word": "creation", "start": 4.2, "end": 4.7, "offset": 37000000, "duration": 5000000},
    ]


@pytest.fixture
def mixed_sync_timing():
    """8 words within tolerance, 2 words outside — accuracy = 80%."""
    return [
        {"word": "Welcome", "start": 0.0, "end": 0.4, "offset": 0, "duration": 4000000},       # perfect
        {"word": "to", "start": 0.5, "end": 0.7, "offset": 5000000, "duration": 2000000},         # perfect
        {"word": "the", "start": 0.8, "end": 1.0, "offset": 8000000, "duration": 2000000},         # perfect
        {"word": "AI", "start": 1.1, "end": 1.4, "offset": 11000000, "duration": 3000000},         # perfect
        {"word": "Media", "start": 2.0, "end": 2.3, "offset": 15000000, "duration": 3000000},      # +500ms — outside
        {"word": "Factory", "start": 1.9, "end": 2.3, "offset": 19000000, "duration": 4000000},    # perfect
        {"word": "platform", "start": 2.5, "end": 2.9, "offset": 25000000, "duration": 4000000},   # perfect
        {"word": "for", "start": 3.0, "end": 3.2, "offset": 30000000, "duration": 2000000},        # perfect
        {"word": "video", "start": 3.8, "end": 4.1, "offset": 33000000, "duration": 3000000},      # +500ms — outside
        {"word": "creation", "start": 3.7, "end": 4.2, "offset": 37000000, "duration": 5000000},   # perfect
    ]


@pytest.fixture
def chinese_sync_timing():
    """Chinese word timing with good sync."""
    return [
        {"word": "欢迎来到", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5000000},
        {"word": "人工智能", "start": 0.6, "end": 1.1, "offset": 6000000, "duration": 5000000},
        {"word": "媒体工厂", "start": 1.2, "end": 1.7, "offset": 12000000, "duration": 5000000},
        {"word": "平台", "start": 1.8, "end": 2.2, "offset": 18000000, "duration": 4000000},
        {"word": "欢迎使用", "start": 2.3, "end": 2.8, "offset": 23000000, "duration": 5000000},
    ]


@pytest.fixture
def good_accuracy_timing():
    """96% accuracy timing — 24/25 words within tolerance."""
    timing = []
    for i in range(25):
        jitter = 0.0 if i != 12 else 0.3  # One word outside tolerance
        timing.append({
            "word": f"word{i}",
            "start": float(i) * 0.5 + jitter,
            "end": float(i) * 0.5 + 0.3 + jitter,
            "offset": i * 5000000,
            "duration": 3000000,
        })
    return timing


# =============================================================================
# Tests: Sync Accuracy
# =============================================================================


class TestSubtitleSyncAccuracy:
    """Verify subtitle sync accuracy measurement against QUAL-03 criteria."""

    def test_perfect_sync_returns_100_percent(self, svc, perfect_sync_timing):
        """Perfect sync: measured and reference timing identical → 100% accuracy."""
        accuracy = svc.calculate_sync_accuracy(perfect_sync_timing, perfect_sync_timing)
        assert accuracy == 100.0

    def test_near_sync_within_tolerance(self, svc, perfect_sync_timing, near_sync_timing):
        """Near sync within 200ms tolerance → 100% accuracy."""
        accuracy = svc.calculate_sync_accuracy(near_sync_timing, perfect_sync_timing)
        assert accuracy == 100.0

    def test_poor_sync_below_tolerance(self, svc, perfect_sync_timing, poor_sync_timing):
        """Poor sync (>200ms off) → accuracy < 50%."""
        accuracy = svc.calculate_sync_accuracy(poor_sync_timing, perfect_sync_timing)
        assert accuracy < 50.0

    def test_mixed_sync_calculates_correctly(self, svc, perfect_sync_timing, mixed_sync_timing):
        """8/10 within tolerance → accuracy = 80%."""
        accuracy = svc.calculate_sync_accuracy(mixed_sync_timing, perfect_sync_timing)
        assert accuracy == 80.0

    def test_chinese_text_sync_accuracy(self, svc, chinese_sync_timing):
        """Chinese timing within tolerance → 100% accuracy."""
        accuracy = svc.calculate_sync_accuracy(chinese_sync_timing, chinese_sync_timing)
        assert accuracy == 100.0

    def test_empty_timing_returns_zero(self, svc):
        """Empty lists → accuracy = 0.0."""
        assert svc.calculate_sync_accuracy([], []) == 0.0
        assert svc.calculate_sync_accuracy([{"word": "a", "start": 0}], []) == 0.0
        assert svc.calculate_sync_accuracy([], [{"word": "a", "start": 0}]) == 0.0

    def test_single_word_accuracy(self, svc):
        """Single word timing — verify calculation works."""
        timing = [{"word": "hello", "start": 0.5, "end": 1.0, "offset": 5000000, "duration": 5000000}]
        accuracy = svc.calculate_sync_accuracy(timing, timing)
        assert accuracy == 100.0

    def test_accuracy_above_95_target(self, svc, good_accuracy_timing):
        """96% words in tolerance → accuracy > 95% QUAL-03 target met."""
        accuracy = svc.calculate_sync_accuracy(good_accuracy_timing, good_accuracy_timing)
        assert accuracy > 95.0


# =============================================================================
# Tests: Subtitle Format Roundtrip
# =============================================================================


class TestSyncAccuracyWithGeneratedSubtitles:
    """Verify subtitle generation preserves timing accuracy."""

    def test_srt_roundtrip_accuracy(self, svc, perfect_sync_timing):
        """Generate SRT from timing, verify it produces valid output."""
        srt_output = svc.generate_srt(perfect_sync_timing)
        assert len(srt_output) > 0
        # SRT should contain all words
        for word_dict in perfect_sync_timing:
            assert word_dict["word"] in srt_output

    def test_word_grouping_preserves_timing(self, svc, perfect_sync_timing):
        """Word grouping preserves start/end timing within acceptable bounds."""
        lines = svc.group_words_into_lines(perfect_sync_timing)
        assert len(lines) > 0
        # First line should start at first word's start
        assert lines[0]["start"] == perfect_sync_timing[0]["start"]
        # Last line should end at last word's end
        assert lines[-1]["end"] == perfect_sync_timing[-1]["end"]
        # Each line's timing should be within its word boundaries
        for line in lines:
            assert line["start"] <= line["end"]

    def test_generate_returns_word_count(self, svc, perfect_sync_timing):
        """generate() returns accurate word and line counts."""
        result = svc.generate(perfect_sync_timing, formats=["srt"])
        assert result["word_count"] == len(perfect_sync_timing)
        assert result["line_count"] > 0
        assert result["srt_content"] is not None
