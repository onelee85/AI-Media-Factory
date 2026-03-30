import litellm
from typing import Optional, List, Dict, Any
from app.config import settings, ModelProviderConfig, ModelConfig
from pydantic import BaseModel


class ModelProviderError(Exception):
    """Raised when all providers fail"""
    pass


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 1000
    provider: Optional[str] = None


class ModelProviderService:
    """
    Unified service for LLM calls with automatic fallback.
    Supports multiple providers: LM Studio, OpenAI, Anthropic, etc.
    """

    def __init__(self, config: ModelConfig = None):
        self.config = config or settings.llm_config
        self._configure_litellm()

    def _configure_litellm(self):
        """Set litellm global settings"""
        litellm.drop_params = True
        litellm.set_verbose = False

    def _build_provider_kwargs(self, provider_config: ModelProviderConfig) -> dict:
        """Build litellm completion kwargs from provider config"""
        kwargs = {
            "model": provider_config.model,
            "base_url": provider_config.base_url,
            "timeout": provider_config.timeout,
        }
        if provider_config.api_key:
            kwargs["api_key"] = provider_config.api_key
        return kwargs

    def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        provider: Optional[str] = None,
        fallback_chain: Optional[List[str]] = None,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Execute chat completion with fallback support.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."}
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            provider: Specific provider to use (overrides default)
            fallback_chain: List of provider names to try in order
            max_retries: Number of retry attempts per provider

        Returns:
            {"content": "...", "usage": {...}, "model": "..."}

        Raises:
            ModelProviderError: If all providers fail
        """
        if fallback_chain is None:
            fallback_chain = ["primary", "fallback"]
        if provider:
            provider_names = [provider]
        else:
            provider_names = fallback_chain

        last_error = None
        for provider_name in provider_names:
            provider_config = self.config.get_provider(provider_name)
            if not provider_config:
                continue

            kwargs = self._build_provider_kwargs(provider_config)

            for attempt in range(max_retries):
                try:
                    response = litellm.completion(
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs,
                    )

                    return {
                        "content": response.choices[0].message.content,
                        "usage": response.usage.model_dump() if response.usage else {},
                        "model": response.model,
                        "provider": provider_name,
                    }

                except Exception as e:
                    last_error = e
                    continue

        raise ModelProviderError(f"All providers failed. Last error: {last_error}")

    async def complete_async(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> Dict[str, Any]:
        """Async wrapper for completion"""
        import asyncio
        return await asyncio.to_thread(self.complete, messages, **kwargs)


model_provider_service = ModelProviderService()
