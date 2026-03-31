"""Subtitle generation and synchronization service.

Converts TTS word-level timing data into SRT and ASS subtitle files
with configurable word grouping, timing sync validation, and export.
"""

import srt
from datetime import timedelta


class SubtitleServiceError(Exception):
    """Subtitle generation error."""
    pass


class SubtitleService:
    """Generates SRT and ASS subtitles from word-level timing data."""

    MAX_CHARS_PER_LINE = 40
    MAX_WORDS_PER_LINE = 8
    MIN_GAP_SECONDS = 0.3
    LINE_BREAK_GAP_SECONDS = 1.5
    SYNC_TOLERANCE_MS = 200

    def group_words_into_lines(self, word_timing: list[dict]) -> list[dict]:
        """Group words into subtitle lines respecting character, word, and timing limits.

        Args:
            word_timing: List of word dicts with 'word', 'start', 'end', 'offset', 'duration'.

        Returns:
            List of line dicts: {text: str, start: float, end: float, words: list[dict]}
        """
        if not word_timing:
            return []

        lines = []
        current_words: list[dict] = []
        current_char_count = 0

        for word_dict in word_timing:
            word_text = word_dict["word"]

            # Check if we should start a new line
            should_break = False

            # 1. Character limit exceeded
            added_chars = len(word_text) + (1 if current_words else 0)  # +1 for space
            if current_char_count + added_chars > self.MAX_CHARS_PER_LINE:
                should_break = True

            # 2. Word count limit exceeded
            if len(current_words) >= self.MAX_WORDS_PER_LINE:
                should_break = True

            # 3. Time gap since last word > threshold
            if current_words:
                gap = word_dict["start"] - current_words[-1]["end"]
                if gap > self.LINE_BREAK_GAP_SECONDS:
                    should_break = True

            if should_break and current_words:
                # Finalize current line
                lines.append({
                    "text": " ".join(w["word"] for w in current_words),
                    "start": current_words[0]["start"],
                    "end": current_words[-1]["end"],
                    "words": list(current_words),
                })
                current_words = []
                current_char_count = 0

            # Add word to current line
            current_words.append(word_dict)
            current_char_count += len(word_text) + (1 if len(current_words) > 1 else 0)

        # Finalize last line
        if current_words:
            lines.append({
                "text": " ".join(w["word"] for w in current_words),
                "start": current_words[0]["start"],
                "end": current_words[-1]["end"],
                "words": list(current_words),
            })

        return lines

    def generate_srt(self, word_timing: list[dict]) -> str:
        """Generate SRT formatted subtitles from word timing data.

        Args:
            word_timing: List of word dicts.

        Returns:
            SRT formatted string.
        """
        lines = self.group_words_into_lines(word_timing)
        if not lines:
            return ""

        subs = []
        for i, line in enumerate(lines, start=1):
            subs.append(srt.Subtitle(
                index=i,
                start=timedelta(seconds=line["start"]),
                end=timedelta(seconds=line["end"]),
                content=line["text"],
            ))

        return srt.compose(subs)

    def generate_ass(self, word_timing: list[dict], title: str = "Subtitle") -> str:
        """Generate ASS (Advanced SubStation Alpha) formatted subtitles.

        Args:
            word_timing: List of word dicts.
            title: Script title for ASS header.

        Returns:
            ASS formatted string.
        """
        lines = self.group_words_into_lines(word_timing)

        sections = []

        # [Script Info]
        sections.append("[Script Info]")
        sections.append(f"Title: {title}")
        sections.append("ScriptType: v4.00+")
        sections.append("WrapStyle: 0")
        sections.append("PlayResX: 1920")
        sections.append("PlayResY: 1080")
        sections.append("")

        # [V4+ Styles]
        sections.append("[V4+ Styles]")
        sections.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")
        sections.append("Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1")
        sections.append("")

        # [Events]
        sections.append("[Events]")
        sections.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

        for line in lines:
            start_str = self._seconds_to_ass_time(line["start"])
            end_str = self._seconds_to_ass_time(line["end"])
            # Replace spaces with \N for ASS line breaks (optional, keep on one line)
            text = line["text"]
            sections.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}")

        return "\n".join(sections) + "\n"

    def _seconds_to_ass_time(self, seconds: float) -> str:
        """Convert seconds to ASS timestamp format H:MM:SS.cc (centiseconds)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        # ASS uses centiseconds (1/100s), not milliseconds
        cs = int(round(secs * 100))
        whole_secs = cs // 100
        centisecs = cs % 100
        return f"{hours}:{minutes:02d}:{whole_secs:02d}.{centisecs:02d}"

    def calculate_sync_accuracy(
        self, word_timing: list[dict], reference_timing: list[dict]
    ) -> float:
        """Measure sync accuracy between measured and reference timing.

        Args:
            word_timing: Measured word timing.
            reference_timing: Reference (ground truth) word timing.

        Returns:
            Percentage (0.0-100.0) of words within SYNC_TOLERANCE_MS.
        """
        if not word_timing or not reference_timing:
            return 0.0

        # Build reference lookup by word text
        ref_by_word: dict[str, list[float]] = {}
        for ref in reference_timing:
            word = ref["word"]
            if word not in ref_by_word:
                ref_by_word[word] = []
            ref_by_word[word].append(ref["start"])

        matched = 0
        within_tolerance = 0

        for measured in word_timing:
            word = measured["word"]
            if word in ref_by_word and ref_by_word[word]:
                ref_start = ref_by_word[word].pop(0)
                matched += 1
                diff_ms = abs(measured["start"] - ref_start) * 1000
                if diff_ms <= self.SYNC_TOLERANCE_MS:
                    within_tolerance += 1

        if matched == 0:
            return 0.0

        return round((within_tolerance / matched) * 100, 1)

    def generate(
        self,
        word_timing: list[dict],
        formats: list[str] | None = None,
        title: str = "Subtitle",
    ) -> dict:
        """Generate subtitle files in specified formats.

        Args:
            word_timing: List of word dicts from TTS output.
            formats: List of format strings ("srt", "ass"). Defaults to both.
            title: Title for ASS header.

        Returns:
            Dict with srt_content, ass_content, word_count, line_count, lines.
        """
        if formats is None:
            formats = ["srt", "ass"]

        lines = self.group_words_into_lines(word_timing)

        srt_content = None
        ass_content = None

        if "srt" in formats:
            srt_content = self.generate_srt(word_timing)
        if "ass" in formats:
            ass_content = self.generate_ass(word_timing, title=title)

        return {
            "srt_content": srt_content,
            "ass_content": ass_content,
            "word_count": len(word_timing),
            "line_count": len(lines),
            "lines": lines,
        }


def generate_subtitles(
    word_timing: list[dict],
    formats: list[str] | None = None,
    title: str = "Subtitle",
) -> dict:
    """Convenience function for one-off subtitle generation."""
    service = SubtitleService()
    return service.generate(word_timing, formats=formats, title=title)
