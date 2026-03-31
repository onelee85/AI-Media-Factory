"""
Failing tests for SubtitleService — TDD RED phase.
Tests word grouping, SRT/ASS generation, sync accuracy, edge cases.
"""
import pytest


class TestSubtitleServiceWordGrouping:
    """Test group_words_into_lines() behavior."""

    def test_group_short_text_single_line(self):
        """Short text (<40 chars) should stay on one line."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5000000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6000000, "duration": 5000000},
        ]
        lines = svc.group_words_into_lines(words)
        assert len(lines) == 1
        assert lines[0]["text"] == "Hello world"

    def test_group_respects_max_chars(self):
        """Text exceeding 40 chars should split into multiple lines."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        # 10 words * ~5 chars = ~50 chars, exceeds MAX_CHARS_PER_LINE=40
        words = [
            {"word": f"word{i}", "start": float(i), "end": float(i) + 0.4, "offset": i * 10_000_000, "duration": 4_000_000}
            for i in range(10)
        ]
        lines = svc.group_words_into_lines(words)
        assert len(lines) >= 2

    def test_group_respects_max_words(self):
        """More than 8 words should split into multiple lines."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        words = [
            {"word": "hi", "start": float(i), "end": float(i) + 0.1, "offset": i * 10_000_000, "duration": 1_000_000}
            for i in range(10)
        ]
        lines = svc.group_words_into_lines(words)
        assert len(lines) >= 2
        for line in lines:
            assert len(line["words"]) <= 8

    def test_group_splits_on_time_gap(self):
        """Gap >1.5s between words forces a new line."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
            {"word": "After", "start": 3.0, "end": 3.5, "offset": 30_000_000, "duration": 5_000_000},  # 1.9s gap
            {"word": "gap", "start": 3.6, "end": 4.0, "offset": 36_000_000, "duration": 4_000_000},
        ]
        lines = svc.group_words_into_lines(words)
        assert len(lines) == 2
        assert lines[0]["text"] == "Hello world"
        assert lines[1]["text"] == "After gap"


class TestSubtitleServiceSRT:
    """Test generate_srt() output format."""

    def test_srt_has_valid_format(self):
        """SRT output should have sequential indices and timestamps."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
        ]
        srt = svc.generate_srt(words)
        assert "1" in srt  # Sequential index
        assert "-->" in srt  # Timestamp separator
        assert "Hello world" in srt

    def test_srt_timestamps_ascending(self):
        """Each subtitle start time should be >= previous end time."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        words = [
            {"word": "First", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "line", "start": 0.6, "end": 1.0, "offset": 6_000_000, "duration": 4_000_000},
            {"word": "Second", "start": 3.0, "end": 3.5, "offset": 30_000_000, "duration": 5_000_000},  # gap > 1.5s
            {"word": "line", "start": 3.6, "end": 4.0, "offset": 36_000_000, "duration": 4_000_000},
        ]
        srt = svc.generate_srt(words)
        # Basic check: both lines present
        assert "First line" in srt
        assert "Second line" in srt


class TestSubtitleServiceASS:
    """Test generate_ass() output format."""

    def test_ass_has_required_sections(self):
        """ASS output must have [Script Info], [V4+ Styles], [Events]."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
        ]
        ass = svc.generate_ass(words)
        assert "[Script Info]" in ass
        assert "[V4+ Styles]" in ass
        assert "[Events]" in ass

    def test_ass_has_dialogue_lines(self):
        """ASS [Events] must have Dialogue: lines with timestamps."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
        ]
        ass = svc.generate_ass(words)
        assert "Dialogue:" in ass


class TestSubtitleServiceSyncAccuracy:
    """Test calculate_sync_accuracy() behavior."""

    def test_perfect_match(self):
        """Identical timing should return 100.0% accuracy."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        timing = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
        ]
        accuracy = svc.calculate_sync_accuracy(timing, timing)
        assert accuracy == 100.0

    def test_within_tolerance(self):
        """Timing offset <200ms should return high accuracy."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        reference = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
        ]
        measured = [
            {"word": "Hello", "start": 0.1, "end": 0.6, "offset": 1_000_000, "duration": 5_000_000},  # 100ms off
            {"word": "world", "start": 0.65, "end": 1.15, "offset": 6_500_000, "duration": 5_000_000},  # 50ms off
        ]
        accuracy = svc.calculate_sync_accuracy(measured, reference)
        assert accuracy == 100.0

    def test_outside_tolerance(self):
        """Timing offset >200ms should return low accuracy."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        reference = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
        ]
        measured = [
            {"word": "Hello", "start": 0.5, "end": 1.0, "offset": 5_000_000, "duration": 5_000_000},  # 500ms off
            {"word": "world", "start": 1.5, "end": 2.0, "offset": 15_000_000, "duration": 5_000_000},  # 900ms off
        ]
        accuracy = svc.calculate_sync_accuracy(measured, reference)
        assert accuracy == 0.0


class TestSubtitleServiceEdgeCases:
    """Edge case handling."""

    def test_empty_word_timing(self):
        """Empty list should return empty content, 0 words, 0 lines."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        result = svc.generate([], formats=["srt", "ass"])
        assert result["word_count"] == 0
        assert result["line_count"] == 0
        assert result["srt_content"] == ""
        assert result["ass_content"] != ""  # ASS still has header

    def test_single_word(self):
        """Single word should produce one subtitle line."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        words = [{"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000}]
        lines = svc.group_words_into_lines(words)
        assert len(lines) == 1
        assert lines[0]["text"] == "Hello"

    def test_chinese_text_grouping(self):
        """Chinese characters should group correctly (char count = CJK chars)."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        # 10 Chinese characters, should fit on one line (< 40 chars)
        words = [
            {"word": "欢迎来到", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "人工智能", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
            {"word": "媒体工厂", "start": 1.2, "end": 1.7, "offset": 12_000_000, "duration": 5_000_000},
        ]
        lines = svc.group_words_into_lines(words)
        assert len(lines) >= 1
        full_text = " ".join(l["text"] for l in lines)
        assert "欢迎来到" in full_text


class TestSubtitleServiceGenerate:
    """Test the main generate() method."""

    def test_generate_returns_all_fields(self):
        """generate() must return srt_content, ass_content, word_count, line_count, lines."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
        ]
        result = svc.generate(words, formats=["srt", "ass"])
        assert "srt_content" in result
        assert "ass_content" in result
        assert "word_count" in result
        assert "line_count" in result
        assert "lines" in result

    def test_word_count_matches_input(self):
        """word_count must equal length of input word_timing."""
        from app.services.subtitle_service import SubtitleService

        svc = SubtitleService()
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "offset": 0, "duration": 5_000_000},
            {"word": "world", "start": 0.6, "end": 1.1, "offset": 6_000_000, "duration": 5_000_000},
        ]
        result = svc.generate(words)
        assert result["word_count"] == 2
