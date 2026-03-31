import json
from typing import Optional, Dict, Any

from app.services.model_provider import model_provider_service, ModelProviderError


SYSTEM_PROMPT = """You are an expert video script writer. Given a topic or brief, produce a structured script
with clear sections. Output valid JSON with this schema:
{
  "title": "Script title",
  "sections": [
    {"heading": "Section name", "content": "Narration text", "duration_estimate_sec": 30}
  ],
  "summary": "One-sentence summary of the script"
}
Only output the JSON object, no extra text."""


class ScriptGeneratorService:
    """
    Generates video scripts using LLM providers.
    Wraps ModelProviderService with script-specific prompts and parsing.
    """

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

        parsed = self._parse_script(result["content"])

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
            data.setdefault("title", "Untitled Script")
            data.setdefault("summary", "")
            return data
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Failed to parse LLM output as script: {exc}")


script_generator_service = ScriptGeneratorService()
