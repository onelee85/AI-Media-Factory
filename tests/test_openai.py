import os

import pytest
from app.services.model_provider import ModelProviderService, ModelProviderError


@pytest.mark.asyncio
async def test_openai_completion():
    """Test OpenAI provider if API key available — skips otherwise."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    service = ModelProviderService()
    result = await service.complete_async(
        messages=[{"role": "user", "content": "Say 'test' in one word"}],
        provider="fallback",
        fallback_chain=[],
    )
    assert result["content"]
    assert result["provider"] == "fallback"


def test_openai_config():
    """Verify OpenAI provider is configured in models.yaml."""
    from app.config import settings

    cfg = settings.llm_config.get_provider("fallback")
    assert cfg is not None, "fallback provider not configured"
    assert cfg.provider == "openai"
    assert cfg.base_url == "https://api.openai.com/v1"
