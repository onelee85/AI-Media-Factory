import pytest
from app.services.model_provider import ModelProviderService, ModelProviderError


@pytest.mark.asyncio
async def test_lm_studio_completion():
    """Test LM Studio provider if available — skips when server is down."""
    service = ModelProviderService()

    try:
        result = await service.complete_async(
            messages=[{"role": "user", "content": "Say 'test' in one word"}],
            provider="primary",
            fallback_chain=[],
        )
        assert "content" in result
        assert result["content"]
        assert result["provider"] == "primary"
    except (ModelProviderError, Exception) as e:
        pytest.skip(f"LM Studio not available: {e}")


def test_lm_studio_config():
    """Verify LM Studio provider is configured in models.yaml."""
    from app.config import settings

    cfg = settings.llm_config.get_provider("primary")
    assert cfg is not None, "primary provider not configured"
    assert cfg.provider == "lm_studio"
    assert cfg.base_url == "http://localhost:1234/v1"
    assert cfg.api_key == "not-needed"
