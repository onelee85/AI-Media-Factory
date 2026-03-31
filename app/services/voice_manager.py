"""Voice manager for edge-tts voice selection.

Provides curated list of Chinese and English voices with filtering.
Supports both static registry and dynamic discovery via edge-tts VoicesManager.
"""
from typing import List, Optional, Dict, Any

# Curated voice registry — high-quality voices for video narration
# Format: {name: {"locale": str, "gender": str, "category": str, "language": str}}
CURATED_VOICES = {
    # Chinese voices (5+ as required by CORE-02)
    "zh-CN-XiaoxiaoNeural": {
        "locale": "zh-CN",
        "gender": "Female",
        "category": "General",
        "language": "zh",
        "description": "Versatile, warm female voice — best default for Chinese narration"
    },
    "zh-CN-YunxiNeural": {
        "locale": "zh-CN",
        "gender": "Male",
        "category": "General",
        "language": "zh",
        "description": "Clear male voice — good for informative content"
    },
    "zh-CN-YunjianNeural": {
        "locale": "zh-CN",
        "gender": "Male",
        "category": "Narration",
        "language": "zh",
        "description": "Professional male narrator voice"
    },
    "zh-CN-XiaoyiNeural": {
        "locale": "zh-CN",
        "gender": "Female",
        "category": "Chat",
        "language": "zh",
        "description": "Casual female voice — good for conversational style"
    },
    "zh-CN-YunyangNeural": {
        "locale": "zh-CN",
        "gender": "Male",
        "category": "News",
        "language": "zh",
        "description": "News anchor male voice — professional, authoritative"
    },
    # English voices (3+ as required by CORE-02)
    "en-US-AriaNeural": {
        "locale": "en-US",
        "gender": "Female",
        "category": "General",
        "language": "en",
        "description": "Natural American English female voice — best default for English"
    },
    "en-US-GuyNeural": {
        "locale": "en-US",
        "gender": "Male",
        "category": "General",
        "language": "en",
        "description": "Clear American English male voice"
    },
    "en-US-JennyNeural": {
        "locale": "en-US",
        "gender": "Female",
        "category": "General",
        "language": "en",
        "description": "Friendly American English female voice"
    },
}

# Default voices per language
DEFAULT_VOICES = {
    "zh": "zh-CN-XiaoxiaoNeural",
    "en": "en-US-AriaNeural",
}


class VoiceManagerService:
    """Manages TTS voice selection and discovery."""

    def list_voices(
        self,
        language: Optional[str] = None,
        gender: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List available voices, optionally filtered by language and gender.

        Args:
            language: Filter by language code ("zh" or "en")
            gender: Filter by gender ("Male" or "Female")

        Returns:
            List of voice dicts with name, locale, gender, category, description
        """
        results = []
        for name, info in CURATED_VOICES.items():
            if language and info["language"] != language:
                continue
            if gender and info["gender"] != gender:
                continue
            results.append({
                "name": name,
                **info,
            })
        return results

    def get_default_voice(self, language: str = "zh") -> str:
        """Get the default voice name for a language.

        Args:
            language: Language code ("zh" or "en")

        Returns:
            Voice name string (e.g., "zh-CN-XiaoxiaoNeural")
        """
        return DEFAULT_VOICES.get(language, DEFAULT_VOICES["zh"])

    def get_voice(self, name: str) -> Optional[Dict[str, Any]]:
        """Get voice info by exact name.

        Args:
            name: Full voice name (e.g., "zh-CN-XiaoxiaoNeural")

        Returns:
            Voice dict or None if not found
        """
        if name in CURATED_VOICES:
            return {"name": name, **CURATED_VOICES[name]}
        return None

    async def discover_voices(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover all available voices from edge-tts service.

        Uses edge-tts VoicesManager for dynamic discovery.
        Falls back to curated list if service unavailable.

        Args:
            language: Filter by language code (e.g., "zh", "en")

        Returns:
            List of voice dicts from edge-tts service
        """
        try:
            from edge_tts import VoicesManager
            voices = await VoicesManager.create()
            if language:
                return voices.find(Language=language)
            return voices.find()
        except Exception:
            # Fallback to curated list
            return self.list_voices(language=language)


# Module-level singleton
voice_manager_service = VoiceManagerService()
