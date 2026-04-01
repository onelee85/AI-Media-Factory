"""Stock media service — Pexels API integration with keyword extraction.

Provides PexelsClient for API search/download, KeywordExtractor for
script section analysis, and StockMediaService for orchestration.
"""
import logging
import re
from pathlib import Path

import httpx

from app.storage import StorageService

logger = logging.getLogger(__name__)


class PexelsClientError(Exception):
    """Raised when Pexels API call fails."""


class PexelsClient:
    """Wrapper for the Pexels REST API — search and download photos."""

    BASE_URL = "https://api.pexels.com/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": api_key}
        self._client = httpx.Client(timeout=30, headers=self.headers)

    def search_photos(
        self,
        query: str,
        per_page: int = 3,
        orientation: str = "landscape",
    ) -> list[dict]:
        """Search Pexels for photos matching query.

        Args:
            query: Search terms string.
            per_page: Number of results to return (max 80).
            orientation: "landscape", "portrait", or "square".

        Returns:
            List of photo dicts with id, src, alt, photographer.
            Empty list if no results found.
        """
        try:
            response = self._client.get(
                f"{self.BASE_URL}/search",
                params={
                    "query": query,
                    "per_page": per_page,
                    "orientation": orientation,
                },
            )
        except httpx.TimeoutException:
            raise PexelsClientError(f"Pexels search timed out for query: {query}")
        except httpx.RequestError as exc:
            raise PexelsClientError(f"Pexels request failed: {exc}")

        if response.status_code == 429:
            raise PexelsClientError("Pexels API rate limit exceeded (429)")
        if response.status_code != 200:
            raise PexelsClientError(
                f"Pexels search failed (HTTP {response.status_code}): {response.text[:200]}"
            )

        data = response.json()
        return data.get("photos", [])

    def download_photo(self, url: str, save_path: Path) -> Path:
        """Download photo from URL to local path.

        Args:
            url: Direct image URL from Pexels src dict.
            save_path: Local file path to write the image.

        Returns:
            The save_path on success.

        Raises:
            PexelsClientError: On HTTP failure.
        """
        try:
            response = self._client.get(url)
        except httpx.TimeoutException:
            raise PexelsClientError(f"Photo download timed out: {url}")
        except httpx.RequestError as exc:
            raise PexelsClientError(f"Photo download failed: {exc}")

        if response.status_code != 200:
            raise PexelsClientError(
                f"Photo download failed (HTTP {response.status_code}): {url}"
            )

        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(response.content)
        return save_path

    def search_and_download(
        self,
        query: str,
        save_dir: Path,
        per_page: int = 1,
        orientation: str = "landscape",
    ) -> list[Path]:
        """Search then download top results to save_dir.

        Args:
            query: Search terms.
            save_dir: Directory to save images.
            per_page: Number of images to fetch.
            orientation: Image orientation.

        Returns:
            List of saved file paths.
        """
        photos = self.search_photos(query, per_page=per_page, orientation=orientation)
        saved = []
        for photo in photos:
            src = photo.get("src", {})
            url = src.get("original") or src.get("large")
            if not url:
                continue
            photo_id = photo.get("id", "unknown")
            save_path = save_dir / f"pexels_{photo_id}.jpg"
            try:
                self.download_photo(url, save_path)
                saved.append(save_path)
            except PexelsClientError as exc:
                logger.warning("Failed to download photo %s: %s", photo_id, exc)
        return saved

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class KeywordExtractor:
    """Extract searchable keywords from script sections."""

    STOP_WORDS_EN = {
        "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
        "to", "for", "of", "with", "and", "or", "but", "not", "this",
        "that", "it", "be", "have", "has", "do", "does", "did", "will",
        "would", "could", "should", "can", "may", "might", "shall", "must",
        "need", "dare", "ought", "used", "i", "you", "he", "she", "we",
        "they", "me", "him", "her", "us", "them", "my", "your", "his",
        "its", "our", "their", "from", "as", "by", "so", "if", "then",
        "than", "too", "very", "just", "about", "also", "into", "over",
        "such", "no", "up", "out", "off", "down", "all", "some", "any",
        "each", "every", "both", "few", "more", "most", "other", "another",
        "same", "been", "being", "am", "s", "t", "re", "ve", "ll", "d",
    }

    def extract_keywords(self, section: dict) -> list[str]:
        """Extract 1-5 searchable keywords from a script section.

        Args:
            section: Dict with "heading" and "content" keys.

        Returns:
            List of keyword strings suitable for image search.
        """
        heading = section.get("heading", "")
        content = section.get("content", "")

        # Check if content is Chinese text (contains CJK characters)
        has_chinese = bool(re.search(r"[\u4e00-\u9fff]", content or heading))

        if has_chinese:
            return self._extract_chinese(heading, content)

        return self._extract_english(heading, content)

    def _extract_english(self, heading: str, content: str) -> list[str]:
        """Extract English keywords from heading and content."""
        # Tokenize heading
        heading_words = re.findall(r"[a-zA-Z]{3,}", heading.lower())

        # Tokenize content
        content_words = re.findall(r"[a-zA-Z]{3,}", content.lower())

        # Filter stop words
        heading_keywords = [w for w in heading_words if w not in self.STOP_WORDS_EN]
        content_keywords = [w for w in content_words if w not in self.STOP_WORDS_EN]

        # If content has < 3 meaningful words, use heading only
        if len(content_keywords) < 3:
            keywords = heading_keywords
        else:
            # Prioritize heading keywords, then content keywords
            keywords = heading_keywords + content_keywords

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)

        # Limit to 5, capitalize for readability
        return [k.capitalize() for k in unique[:5]] if unique else [heading.strip()] if heading.strip() else []

    def _extract_chinese(self, heading: str, content: str) -> list[str]:
        """Extract Chinese keywords from heading and content."""
        # Split by common Chinese punctuation and spaces
        segments = re.split(r"[，。！？；：、\s]+", f"{heading} {content}")

        # Keep meaningful segments (> 1 char, not pure punctuation)
        keywords = []
        for seg in segments:
            seg = seg.strip()
            if len(seg) > 1 and re.search(r"[\u4e00-\u9fff]", seg):
                keywords.append(seg)

        # Deduplicate
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)

        return unique[:5] if unique else [heading.strip()] if heading.strip() else []

    def build_search_query(self, keywords: list[str]) -> str:
        """Join keywords into a single Pexels search query.

        Uses space-separated format for best Pexels results.
        Max 100 chars (Pexels query limit).
        """
        query = " ".join(keywords)
        return query[:100] if len(query) > 100 else query


class StockMediaService:
    """Orchestrates keyword extraction + Pexels search for an entire script."""

    def __init__(
        self,
        pexels_client: PexelsClient,
        keyword_extractor: KeywordExtractor | None = None,
        storage: StorageService | None = None,
    ):
        self.pexels = pexels_client
        self.keywords = keyword_extractor or KeywordExtractor()
        self.storage = storage or StorageService()

    def match_images_to_script(
        self,
        script_sections: list[dict],
        save_dir: Path,
        images_per_section: int = 1,
    ) -> list[list[Path]]:
        """For each script section, extract keywords → search Pexels → download images.

        Args:
            script_sections: List of section dicts from script generator output.
            save_dir: Directory to save downloaded images.
            images_per_section: Number of images to fetch per section (default 1).

        Returns:
            List of lists: [[section_0_image_paths], [section_1_image_paths], ...]
            Empty inner list if no images found for that section.
        """
        all_results = []

        for idx, section in enumerate(script_sections):
            # Extract keywords
            keywords = self.keywords.extract_keywords(section)
            if not keywords:
                logger.warning("No keywords extracted for section %d", idx)
                all_results.append([])
                continue

            query = self.keywords.build_search_query(keywords)

            # Search and download
            section_dir = save_dir / f"section_{idx}"
            try:
                paths = self.pexels.search_and_download(
                    query=query,
                    save_dir=section_dir,
                    per_page=images_per_section,
                    orientation="landscape",
                )
                if paths:
                    # Rename with section index for ordering
                    renamed = []
                    for i, path in enumerate(paths):
                        new_name = f"pexels_{path.stem}_s{idx}.jpg"
                        new_path = save_dir / new_name
                        if new_path != path:
                            path.rename(new_path)
                        renamed.append(new_path)
                    # Clean up empty section dir
                    if section_dir.exists() and not any(section_dir.iterdir()):
                        section_dir.rmdir()
                    all_results.append(renamed)
                else:
                    logger.warning(
                        "No images found for section %d (query: %s)", idx, query
                    )
                    all_results.append([])
            except PexelsClientError as exc:
                logger.error("Pexels error for section %d: %s", idx, exc)
                all_results.append([])

        return all_results
