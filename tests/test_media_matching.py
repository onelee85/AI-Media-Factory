"""Tests for stock media matching — Phase 7.

Tests keyword extraction (KeywordExtractor) and media service logic.
Pexels API tests are skipped by default (require API key).
"""
import pytest
from pathlib import Path

from app.services.media_service import (
    KeywordExtractor,
    PexelsClient,
    PexelsClientError,
    StockMediaService,
)


# =============================================================================
# Test: KeywordExtractor
# =============================================================================


class TestKeywordExtractor:
    """Tests for keyword extraction from script sections."""

    def setup_method(self):
        self.extractor = KeywordExtractor()

    def test_extract_keywords_english(self):
        """English section produces relevant keywords."""
        section = {
            "heading": "The Future of Artificial Intelligence",
            "content": "Artificial intelligence is transforming healthcare, finance, and transportation across the globe.",
        }
        keywords = self.extractor.extract_keywords(section)
        assert len(keywords) >= 1
        assert len(keywords) <= 5
        # Should include meaningful words, not just stop words
        kw_lower = [k.lower() for k in keywords]
        assert any(
            w in kw_lower
            for w in [
                "artificial",
                "intelligence",
                "healthcare",
                "finance",
                "transportation",
                "future",
            ]
        )

    def test_extract_keywords_chinese(self):
        """Chinese section produces keywords."""
        section = {
            "heading": "人工智能的未来",
            "content": "人工智能正在改变医疗、金融和交通等各个行业。",
        }
        keywords = self.extractor.extract_keywords(section)
        assert len(keywords) >= 1
        # Chinese keywords should be preserved
        assert any(
            "人工智能" in k or "医疗" in k or "金融" in k for k in keywords
        )

    def test_extract_keywords_empty_content(self):
        """Empty content falls back to heading."""
        section = {"heading": "Technology", "content": ""}
        keywords = self.extractor.extract_keywords(section)
        assert len(keywords) >= 1
        assert "technology" in [k.lower() for k in keywords]

    def test_extract_keywords_short_content(self):
        """Very short content (< 3 words) uses heading."""
        section = {"heading": "Ocean Waves", "content": "Water flows."}
        keywords = self.extractor.extract_keywords(section)
        assert len(keywords) >= 1

    def test_extract_keywords_all_stop_words(self):
        """Content with only stop words falls back to heading."""
        section = {
            "heading": "Machine Learning",
            "content": "This is the and it for of with.",
        }
        keywords = self.extractor.extract_keywords(section)
        assert len(keywords) >= 1
        kw_lower = [k.lower() for k in keywords]
        assert "machine" in kw_lower or "learning" in kw_lower

    def test_build_search_query(self):
        """Keywords join into search query."""
        keywords = ["AI", "technology", "robot"]
        query = self.extractor.build_search_query(keywords)
        assert query == "AI technology robot"

    def test_build_search_query_truncates(self):
        """Long queries are truncated to 100 chars."""
        keywords = ["word"] * 30  # 5 chars per word * 30 = 150+ chars
        query = self.extractor.build_search_query(keywords)
        assert len(query) <= 100

    def test_build_search_query_empty(self):
        """Empty keywords produce empty query."""
        assert self.extractor.build_search_query([]) == ""


# =============================================================================
# Test: Stop word filtering
# =============================================================================


class TestKeywordExtractorStopWords:
    """Verify stop words are filtered out."""

    def setup_method(self):
        self.extractor = KeywordExtractor()

    def test_common_stop_words_filtered(self):
        """Common English stop words are removed."""
        section = {
            "heading": "The Topic",
            "content": "This is a test of the system and it works with the data.",
        }
        keywords = self.extractor.extract_keywords(section)
        kw_lower = [k.lower() for k in keywords]
        # Stop words should NOT appear
        for sw in ["the", "is", "a", "of", "and", "it", "with"]:
            assert sw not in kw_lower


# =============================================================================
# Test: Deduplication
# =============================================================================


class TestKeywordDeduplication:
    """Verify keywords are deduplicated."""

    def setup_method(self):
        self.extractor = KeywordExtractor()

    def test_duplicate_words_deduplicated(self):
        """Repeated words should appear only once."""
        section = {
            "heading": "Cloud Computing",
            "content": "Cloud computing enables cloud storage and cloud services for cloud applications.",
        }
        keywords = self.extractor.extract_keywords(section)
        kw_lower = [k.lower() for k in keywords]
        # 'cloud' should appear only once
        assert kw_lower.count("cloud") == 1

    def test_max_five_keywords(self):
        """Should never return more than 5 keywords."""
        section = {
            "heading": "Software Engineering Best Practices",
            "content": "Software engineering involves design, development, testing, deployment, monitoring, debugging, refactoring, and documentation.",
        }
        keywords = self.extractor.extract_keywords(section)
        assert len(keywords) <= 5


# =============================================================================
# Test: PexelsClientError
# =============================================================================


class TestPexelsClientError:
    """Verify PexelsClientError exception behavior."""

    def test_is_exception(self):
        """PexelsClientError should be an Exception subclass."""
        assert issubclass(PexelsClientError, Exception)

    def test_can_be_raised_and_caught(self):
        """Should be raisable and catchable."""
        with pytest.raises(PexelsClientError):
            raise PexelsClientError("test error")


# =============================================================================
# Test: Live Pexels API (skip if no key)
# =============================================================================


@pytest.mark.skipif(
    not __import__("os").getenv("PEXELS_API_KEY"),
    reason="PEXELS_API_KEY not set — skipping live API tests",
)
class TestPexelsClientLive:
    """Live API tests — only run when PEXELS_API_KEY is set."""

    def test_search_photos_returns_results(self):
        """Search for common term returns at least 1 photo."""
        import os

        client = PexelsClient(api_key=os.environ["PEXELS_API_KEY"])
        try:
            photos = client.search_photos("nature landscape", per_page=1)
            assert len(photos) >= 1
            assert "src" in photos[0]
            assert "original" in photos[0]["src"] or "large" in photos[0]["src"]
        finally:
            client.close()

    def test_search_photos_empty_query_handled(self):
        """Unusual query returns empty list, not error."""
        import os

        client = PexelsClient(api_key=os.environ["PEXELS_API_KEY"])
        try:
            photos = client.search_photos("xyzzyplugh42", per_page=1)
            assert isinstance(photos, list)  # May be empty, that's OK
        finally:
            client.close()
