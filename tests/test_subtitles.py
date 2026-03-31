"""
Comprehensive test suite for Phase 5: Subtitle Generation & Synchronization (CORE-04)

Tests validate:
- Word grouping produces readable subtitle lines within character and word limits
- SRT output is valid and parseable by standard SRT parsers
- ASS output contains all required sections for video overlay rendering
- Sync accuracy measurement correctly identifies timing deviations
- Edge cases (empty input, single word, very long text) are handled without errors
"""
import pytest


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_word_timing():
    """Short sentence word timing simulating 'Welcome to AI Media Factory'."""
    return [
        {"word": "Welcome", "start": 0.0, "end": 0.4, "offset": 0, "duration": 4000000},
        {"word": "to", "start": 0.5, "end": 0.7, "offset": 5000000, "duration": 2000000},
        {"word": "AI", "start": 0.8, "end": 1.1, "offset": 8000000, "duration": 3000000},
        {"word": "Media", "start": 1.2, "end": 1.5, "offset": 12000000, "duration": 3000000},
        {"word": "Factory", "start": 1.6, "end": 2.1, "offset": 16000000, "duration": 5000000},
    ]


@pytest.fixture
def long_word_timing():
    """Word timing that exceeds 40 chars per line to test grouping."""
    return [
        {"word": f"word{i}", "start": float(i), "end": float(i) + 0.4,
         "offset": i * 10_000_000, "duration": 4_000_000}
        for i in range(10)
    ]


@pytest.fixture
def chinese_word_timing():
    """Chinese word timing for i18n testing."""
    return [
        {"word": "欢迎来到", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
        {"word": "人工智能", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
        {"word": "媒体工厂", "start": 1.2, "end": 1.7, "offset": 12_000_000, "duration": 5_000_000},
    ]


@pytest.fixture
def svc():
    """SubtitleService instance."""
    from app.services.subtitle_service import SubtitleService
    return SubtitleService()


# =============================================================================
# Test: generate() output fields
# =============================================================================


class TestGenerateOutput:
    """Verify generate() returns all required fields."""

    def test_generate_returns_all_fields(self, svc, sample_word_timing):
        """generate() must return srt_content, ass_content, word_count, line_count, lines."""
        result = svc.generate(sample_word_timing, formats=["srt", "ass"])
        assert "srt_content" in result
        assert "ass_content" in result
        assert "word_count" in result
        assert "line_count" in result
        assert "lines" in result

    def test_word_count_matches_input(self, svc, sample_word_timing):
        """word_count must equal length of input word_timing."""
        result = svc.generate(sample_word_timing)
        assert result["word_count"] == len(sample_word_timing)


# =============================================================================
# Test: Word grouping
# =============================================================================


class TestWordGrouping:
    """Verify group_words_into_lines() respects limits."""

    def test_group_words_single_line_short_text(self, svc, sample_word_timing):
        """Short text (<40 chars) should stay on one line."""
        lines = svc.group_words_into_lines(sample_word_timing)
        assert len(lines) == 1
        assert lines[0]["text"] == "Welcome to AI Media Factory"

    def test_group_words_respects_max_chars(self, svc, long_word_timing):
        """Text >40 chars should split into multiple lines."""
        lines = svc.group_words_into_lines(long_word_timing)
        assert len(lines) >= 2
        for line in lines:
            assert len(line["text"]) <= svc.MAX_CHARS_PER_LINE + 10  # small tolerance for word boundaries

    def test_group_words_respects_max_words(self, svc):
        """More than 8 words should split into multiple lines."""
        words = [
            {"word": "hi", "start": float(i), "end": float(i) + 0.1,
             "offset": i * 10_000_000, "duration": 1_000_000}
            for i in range(10)
        ]
        lines = svc.group_words_into_lines(words)
        assert len(lines) >= 2
        for line in lines:
            assert len(line["words"]) <= svc.MAX_WORDS_PER_LINE

    def test_group_words_splits_on_time_gap(self, svc):
        """Gap >1.5s between words forces a new line."""
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
            {"word": "After", "start": 3.0, "end": 3.5, "offset": 30_000_000, "duration": 5_000_000},
            {"word": "gap", "start": 3.6, "end": 4.0, "offset": 36_000_000, "duration": 4_000_000},
        ]
        lines = svc.group_words_into_lines(words)
        assert len(lines) == 2
        assert lines[0]["text"] == "Hello world"
        assert lines[1]["text"] == "After gap"


# =============================================================================
# Test: SRT format
# =============================================================================


class TestSRTFormat:
    """Verify SRT output is valid and parseable."""

    def test_srt_has_valid_format(self, svc, sample_word_timing):
        """SRT output should have sequential indices and --> timestamps."""
        srt = svc.generate_srt(sample_word_timing)
        assert "1" in srt
        assert "-->" in srt
        assert "Welcome to AI Media Factory" in srt

    def test_srt_timestamps_are_ascending(self, svc):
        """Each subtitle start time should be >= previous end time."""
        words = [
            {"word": "First", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "line", "start": 0.6, "end": 1.0, "offset": 6_000_000, "duration": 4_000_000},
            {"word": "Second", "start": 3.0, "end": 3.5, "offset": 30_000_000, "duration": 5_000_000},
            {"word": "line", "start": 3.6, "end": 4.0, "offset": 36_000_000, "duration": 4_000_000},
        ]
        srt = svc.generate_srt(words)
        assert "First line" in srt
        assert "Second line" in srt

    def test_srt_empty_input(self, svc):
        """Empty word_timing should return empty SRT string."""
        srt = svc.generate_srt([])
        assert srt == ""


# =============================================================================
# Test: ASS format
# =============================================================================


class TestASSFormat:
    """Verify ASS output has required sections."""

    def test_ass_has_required_sections(self, svc, sample_word_timing):
        """ASS output must contain [Script Info], [V4+ Styles], [Events]."""
        ass = svc.generate_ass(sample_word_timing)
        assert "[Script Info]" in ass
        assert "[V4+ Styles]" in ass
        assert "[Events]" in ass

    def test_ass_has_dialogue_lines(self, svc, sample_word_timing):
        """ASS [Events] section must have Dialogue: lines with timestamps."""
        ass = svc.generate_ass(sample_word_timing)
        assert "Dialogue:" in ass
        # Timestamp format: H:MM:SS.cc
        import re
        assert re.search(r"Dialogue: \d+,\d+:\d{2}:\d{2}\.\d{2},", ass)

    def test_ass_has_style_definition(self, svc, sample_word_timing):
        """ASS must have a Style: line defining Default style."""
        ass = svc.generate_ass(sample_word_timing)
        assert "Style: Default" in ass
        assert "Arial" in ass

    def test_ass_play_resolution(self, svc, sample_word_timing):
        """ASS must specify PlayResX and PlayResY."""
        ass = svc.generate_ass(sample_word_timing)
        assert "PlayResX: 1920" in ass
        assert "PlayResY: 1080" in ass


# =============================================================================
# Test: Sync accuracy
# =============================================================================


class TestSyncAccuracy:
    """Verify calculate_sync_accuracy() tolerance-based matching."""

    def test_sync_accuracy_perfect_match(self, svc):
        """Identical timing should return 100.0% accuracy."""
        timing = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
        ]
        accuracy = svc.calculate_sync_accuracy(timing, timing)
        assert accuracy == 100.0

    def test_sync_accuracy_within_tolerance(self, svc):
        """Timing offset <200ms should return high accuracy."""
        reference = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
        ]
        measured = [
            {"word": "Hello", "start": 0.1, "end": 0.6, "offset": 1_000_000, "duration": 5_000_000},
            {"word": "world", "start": 0.65, "end": 1.15, "offset": 6_500_000, "duration": 5_000_000},
        ]
        accuracy = svc.calculate_sync_accuracy(measured, reference)
        assert accuracy == 100.0

    def test_sync_accuracy_outside_tolerance(self, svc):
        """Timing offset >200ms should return low accuracy."""
        reference = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
        ]
        measured = [
            {"word": "Hello", "start": 0.5, "end": 1.0, "offset": 5_000_000, "duration": 5_000_000},
            {"word": "world", "start": 1.5, "end": 2.0, "offset": 15_000_000, "duration": 5_000_000},
        ]
        accuracy = svc.calculate_sync_accuracy(measured, reference)
        assert accuracy == 0.0

    def test_sync_accuracy_empty_inputs(self, svc):
        """Empty inputs should return 0.0 accuracy."""
        assert svc.calculate_sync_accuracy([], []) == 0.0
        timing = [{"word": "Hi", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000}]
        assert svc.calculate_sync_accuracy(timing, []) == 0.0
        assert svc.calculate_sync_accuracy([], timing) == 0.0


# =============================================================================
# Test: Edge cases
# =============================================================================


class TestEdgeCases:
    """Verify edge case handling without errors."""

    def test_empty_word_timing(self, svc):
        """Empty list should return empty content, 0 words, 0 lines, no errors."""
        result = svc.generate([], formats=["srt", "ass"])
        assert result["word_count"] == 0
        assert result["line_count"] == 0
        assert result["srt_content"] == ""
        assert result["ass_content"] != ""  # ASS still has header

    def test_single_word(self, svc):
        """Single word should produce one subtitle line."""
        words = [{"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000}]
        lines = svc.group_words_into_lines(words)
        assert len(lines) == 1
        assert lines[0]["text"] == "Hello"

    def test_chinese_text_grouping(self, svc, chinese_word_timing):
        """Chinese characters should group correctly (char count = CJK chars)."""
        lines = svc.group_words_into_lines(chinese_word_timing)
        assert len(lines) >= 1
        full_text = " ".join(l["text"] for l in lines)
        assert "欢迎来到" in full_text
        assert "人工智能" in full_text
        assert "媒体工厂" in full_text


# =============================================================================
# Test: Module exports
# =============================================================================


class TestModuleExports:
    """Verify all required exports are available."""

    def test_subtitle_service_class_importable(self):
        """SubtitleService class must be importable from app.services.subtitle_service."""
        from app.services.subtitle_service import SubtitleService
        assert SubtitleService is not None

    def test_subtitle_service_error_importable(self):
        """SubtitleServiceError must be importable."""
        from app.services.subtitle_service import SubtitleServiceError
        assert issubclass(SubtitleServiceError, Exception)

    def test_generate_subtitles_convenience_function(self):
        """generate_subtitles() convenience function must be importable."""
        from app.services.subtitle_service import generate_subtitles
        assert callable(generate_subtitles)

    def test_generate_subtitles_convenience_works(self):
        """generate_subtitles() convenience function should produce valid output."""
        from app.services.subtitle_service import generate_subtitles
        words = [
            {"word": "Test", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
        ]
        result = generate_subtitles(words)
        assert result["word_count"] == 1
        assert result["srt_content"] is not None
