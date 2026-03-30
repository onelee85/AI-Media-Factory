import os
import yaml
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class ModelProviderConfig(BaseSettings):
    """Configuration for a single LLM provider."""

    provider: str
    model: str
    base_url: str
    api_key: Optional[str] = None
    timeout: int = 60


class ModelConfig(BaseSettings):
    """Loads and resolves model provider definitions from a YAML file."""

    models_config_path: Path = Path("config/models.yaml")
    default_provider: str = "primary"

    _providers: dict = {}

    def load_providers(self) -> dict:
        """Load provider configs from the YAML file, resolving ${ENV_VAR} patterns."""
        with open(self.models_config_path) as f:
            config = yaml.safe_load(f)

        providers = {}
        for name, cfg in config.get("providers", {}).items():
            api_key = cfg.get("api_key", "")
            if api_key.startswith("${") and api_key.endswith("}"):
                env_var = api_key[2:-1]
                api_key = os.getenv(env_var, "")
            providers[name] = ModelProviderConfig(
                provider=cfg["provider"],
                model=cfg["model"],
                base_url=cfg["base_url"],
                api_key=api_key if api_key else None,
                timeout=cfg.get("timeout", 60),
            )

        self._providers = providers
        return providers

    @property
    def providers(self) -> dict:
        if not self._providers:
            self.load_providers()
        return self._providers

    def get_provider(self, name: str = None) -> Optional[ModelProviderConfig]:
        """Return a provider config by name, falling back to default_provider."""
        name = name or self.default_provider
        return self.providers.get(name)


class Settings(BaseSettings):
    app_name: str = "AI-Media-Factory"
    debug: bool = False
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_media_factory"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/ai_media_factory"
    storage_root: Path = Path("./storage")
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    celery_queues: tuple = ("tts", "media", "render", "compose")
    open_api_base: str = ""
    open_api_key: str = ""
    llm_config: ModelConfig = ModelConfig()

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
