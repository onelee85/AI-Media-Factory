import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services import ModelProviderService, ModelProviderError
from app.config import ModelConfig, ModelProviderConfig


class TestConfigLoadsFromYaml:

    def test_config_loads_from_yaml(self, tmp_path):
        """Test that config loads providers from a YAML file"""
        config_path = tmp_path / "models.yaml"
        config_path.write_text(yaml.dump({
            "providers": {
                "test_provider": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-test",
                    "timeout": 30,
                },
            },
            "default_provider": "test_provider",
        }))

        config = ModelConfig(models_config_path=config_path)
        providers = config.load_providers()

        assert "test_provider" in providers
        assert providers["test_provider"].model == "gpt-4o-mini"
        assert providers["test_provider"].base_url == "https://api.openai.com/v1"
        assert providers["test_provider"].api_key == "sk-test"
        assert providers["test_provider"].timeout == 30

    def test_config_resolves_env_var_api_key(self, tmp_path, monkeypatch):
        """Test that ${ENV_VAR} patterns in api_key are resolved"""
        monkeypatch.setenv("TEST_API_KEY", "sk-resolved-secret")
        config_path = tmp_path / "models.yaml"
        config_path.write_text(yaml.dump({
            "providers": {
                "env_provider": {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "${TEST_API_KEY}",
                    "timeout": 60,
                },
            },
            "default_provider": "env_provider",
        }))

        config = ModelConfig(models_config_path=config_path)
        providers = config.load_providers()

        assert providers["env_provider"].api_key == "sk-resolved-secret"

    def test_config_loads_multiple_providers(self, tmp_path):
        """Test loading YAML with multiple providers"""
        config_path = tmp_path / "models.yaml"
        config_path.write_text(yaml.dump({
            "providers": {
                "local": {
                    "provider": "lm_studio",
                    "model": "local-model",
                    "base_url": "http://localhost:1234/v1",
                    "api_key": "not-needed",
                    "timeout": 120,
                },
                "cloud": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-cloud",
                    "timeout": 60,
                },
            },
            "default_provider": "local",
        }))

        config = ModelConfig(models_config_path=config_path)
        providers = config.load_providers()

        assert len(providers) == 2
        assert "local" in providers
        assert "cloud" in providers

    def test_get_provider_falls_back_to_default(self, tmp_path):
        """Test get_provider returns default when name is None"""
        config_path = tmp_path / "models.yaml"
        config_path.write_text(yaml.dump({
            "providers": {
                "my_default": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-test",
                },
            },
            "default_provider": "my_default",
        }))

        config = ModelConfig(
            models_config_path=config_path,
            default_provider="my_default",
        )
        config.load_providers()

        assert config.get_provider() is not None
        assert config.get_provider().model == "gpt-4o-mini"

    def test_get_provider_returns_none_for_unknown(self, tmp_path):
        """Test get_provider returns None for unknown provider name"""
        config_path = tmp_path / "models.yaml"
        config_path.write_text(yaml.dump({
            "providers": {
                "only_one": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-test",
                },
            },
            "default_provider": "only_one",
        }))

        config = ModelConfig(
            models_config_path=config_path,
            default_provider="only_one",
        )
        config.load_providers()

        assert config.get_provider("nonexistent") is None


class TestProviderSwitching:

    def test_provider_switching(self):
        """Test specifying a different provider via the provider kwarg"""
        config = ModelConfig(models_config_path=Path("config/models.yaml"))
        config.load_providers()
        service = ModelProviderService(config=config)

        # Both providers should be accessible from config
        assert config.get_provider("primary") is not None
        assert config.get_provider("fallback") is not None
        assert config.get_provider("primary") != config.get_provider("fallback")

    def test_provider_override_routes_to_specified(self, tmp_path):
        """Test that provider kwarg routes completion to correct provider"""
        config_path = tmp_path / "models.yaml"
        config_path.write_text(yaml.dump({
            "providers": {
                "alpha": {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-alpha",
                },
                "beta": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-beta",
                },
            },
            "default_provider": "alpha",
        }))
        config = ModelConfig(models_config_path=config_path)
        config.load_providers()
        service = ModelProviderService(config=config)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "hello"
        mock_response.usage = None
        mock_response.model = "gpt-4o-mini"

        with patch("litellm.completion", return_value=mock_response) as mock_call:
            result = service.complete(
                messages=[{"role": "user", "content": "hi"}],
                provider="beta",
                fallback_chain=[],
            )

            call_kwargs = mock_call.call_args[1]
            assert call_kwargs["model"] == "gpt-4o-mini"
            assert result["provider"] == "beta"


class TestFallbackChain:

    def test_fallback_chain_tries_next_on_failure(self):
        """Test that fallback chain moves to next provider when primary fails"""
        config = ModelConfig(models_config_path=Path("config/models.yaml"))
        config.load_providers()
        service = ModelProviderService(config=config)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "fallback worked"
        mock_response.usage = MagicMock()
        mock_response.usage.model_dump.return_value = {"total_tokens": 10}
        mock_response.model = "gpt-4o-mini"

        call_count = 0

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("primary unreachable")
            return mock_response

        with patch("litellm.completion", side_effect=side_effect):
            result = service.complete(
                messages=[{"role": "user", "content": "test"}],
                fallback_chain=["primary", "fallback"],
                max_retries=1,
            )

            assert result["content"] == "fallback worked"
            assert call_count == 2

    def test_fallback_chain_default_order(self):
        """Test that default fallback chain is ['primary', 'fallback']"""
        config = ModelConfig(models_config_path=Path("config/models.yaml"))
        config.load_providers()
        service = ModelProviderService(config=config)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "ok"
        mock_response.usage = None
        mock_response.model = "test"

        observed_models = []

        def track_calls(**kwargs):
            observed_models.append(kwargs["model"])
            return mock_response

        with patch("litellm.completion", side_effect=track_calls):
            service.complete(
                messages=[{"role": "user", "content": "hi"}],
                fallback_chain=["primary", "fallback"],
                max_retries=1,
            )

            # primary should be tried first and succeed, so only one call
            assert len(observed_models) == 1


class TestAllProvidersFail:

    def test_all_providers_fail(self):
        """Test ModelProviderError is raised when every provider fails"""
        config = ModelConfig(models_config_path=Path("config/models.yaml"))
        config.load_providers()
        service = ModelProviderService(config=config)

        with patch("litellm.completion", side_effect=ConnectionError("down")):
            with pytest.raises(ModelProviderError, match="All providers failed"):
                service.complete(
                    messages=[{"role": "user", "content": "test"}],
                    fallback_chain=["primary", "fallback"],
                    max_retries=1,
                )

    def test_invalid_provider_raises_error(self):
        """Test that a nonexistent provider with empty fallback raises error"""
        config = ModelConfig(models_config_path=Path("config/models.yaml"))
        config.load_providers()
        service = ModelProviderService(config=config)

        with pytest.raises(ModelProviderError):
            service.complete(
                messages=[{"role": "user", "content": "test"}],
                provider="nonexistent",
                fallback_chain=[],
            )


class TestChatCompletionModels:

    def test_chat_completion_request_validation(self):
        """Test ChatCompletionRequest accepts valid messages"""
        from app.services.model_provider import ChatCompletionRequest, ChatMessage

        req = ChatCompletionRequest(
            messages=[
                ChatMessage(role="user", content="Hello"),
                ChatMessage(role="assistant", content="Hi there!"),
                ChatMessage(role="user", content="How are you?"),
            ],
            temperature=0.5,
            max_tokens=100,
        )
        assert len(req.messages) == 3
        assert req.temperature == 0.5
        assert req.max_tokens == 100
        assert req.provider is None

    def test_chat_completion_request_defaults(self):
        """Test ChatCompletionRequest default values"""
        from app.services.model_provider import ChatCompletionRequest, ChatMessage

        req = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="test")]
        )
        assert req.temperature == 0.7
        assert req.max_tokens == 1000


class TestHealthEndpointModels:

    @pytest.mark.asyncio
    async def test_health_endpoint_includes_models(self):
        """Test that /api/health response includes models section"""
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert "checks" in data
            assert "models" in data["checks"]
            assert isinstance(data["checks"]["models"], dict)
