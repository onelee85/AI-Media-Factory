import json
from typing import Optional, Dict, Any

from app.services.model_provider import model_provider_service, ModelProviderError


SYSTEM_PROMPT = """Write a video script in JSON format:
{"title": "title", "sections": [{"heading": "name", "content": "text min 30 chars", "duration_estimate_sec": 3}], "summary": "one sentence"}
Each section content must be at least 30 characters. Generate 2 sections. Only output JSON."""


class ScriptGeneratorService:
    """
    Generates video scripts using LLM providers.
    Wraps ModelProviderService with script-specific prompts and parsing.
    """

    MIN_CONTENT_LENGTH = 30  # Minimum characters per section for quality narration

    def __init__(self):
        self.provider = model_provider_service

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        provider: Optional[str] = None,
        fallback_chain: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a script from a user prompt.

        Args:
            prompt: User's topic or brief for the script
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Max tokens to generate
            provider: Specific provider name to use
            fallback_chain: Ordered list of provider names to try

        Returns:
            {
                "title": str,
                "sections": [{"heading": str, "content": str, "duration_estimate_sec": int}],
                "summary": str,
                "raw_content": str,
                "usage": {...},
                "model": str,
                "provider": str,
            }

        Raises:
            ModelProviderError: If all providers fail
            ValueError: If LLM response cannot be parsed as valid script JSON
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        result = self.provider.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            provider=provider,
            fallback_chain=fallback_chain,
        )

        content = result.get("content", "")
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"LLM result keys: {list(result.keys())}")
        logger.info(f"LLM content type: {type(content)}, len: {len(content) if content else 0}")
        
        if not content:
            logger.error("LLM content is empty!")
            raise ValueError("LLM returned empty response")
        
        logger.info(f"LLM raw response: {content[:500]}")

        parsed = self._parse_script(content)

        return {
            **parsed,
            "raw_content": result["content"],
            "usage": result.get("usage", {}),
            "model": result.get("model", ""),
            "provider": result.get("provider", ""),
        }

    async def generate_async(
        self,
        prompt: str,
        **kwargs,
    ) -> Dict[str,Any]:
        """Async wrapper for script generation."""
        import asyncio
        return await asyncio.to_thread(self.generate, prompt, **kwargs)

    @staticmethod
    def _parse_script(raw: str) -> Dict[str, Any]:
        """
        Parse LLM output into a structured script dict.
        Attempts JSON parsing first; falls back to wrapping raw text.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"_parse_script called with raw type: {type(raw)}, len: {len(raw) if raw else 0}")
        
        if not raw:
            logger.error("_parse_script: raw is empty!")
            raise ValueError("LLM returned empty response")
        raw = raw.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            # Remove first line (```json or ```) and last line (```)
            raw = "\n".join(lines[1:-1]).strip()

        try:
            data = json.loads(raw)
            # Validate required fields
            if not isinstance(data, dict):
                raise ValueError("Script JSON must be an object")
            if "sections" not in data or not isinstance(data.get("sections"), list):
                raise ValueError("Script JSON must contain a 'sections' array")
            if len(data["sections"]) < 1:
                raise ValueError("Script must have at least 1 section")

            # Validate section content quality
            for i, section in enumerate(data["sections"]):
                content = section.get("content", "")
                if len(content) < ScriptGeneratorService.MIN_CONTENT_LENGTH:
                    raise ValueError(
                        f"Section {i} content too short ({len(content)} < "
                        f"{ScriptGeneratorService.MIN_CONTENT_LENGTH} chars)"
                    )

            data.setdefault("title", "Untitled Script")
            data.setdefault("summary", "")
            return data
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Failed to parse LLM output as script: {exc}")


script_generator_service = ScriptGeneratorService()
