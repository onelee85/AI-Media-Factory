import os
import yaml
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


def _resolve_env_var(value: str) -> str:
    """Resolve ${ENV_VAR} pattern in config values."""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.getenv(env_var, "")
    return value


class RedisConfig(BaseSettings):
    """Redis connection configuration - loads from config/redis.yaml."""
    
    _config_path: Path = Path("config/redis.yaml")
    _loaded: bool = False

    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_from_yaml()

    def _load_from_yaml(self):
        """Load configuration from YAML file."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                config = yaml.safe_load(f)
            for key, value in config.items():
                resolved = _resolve_env_var(value)
                if hasattr(self, key):
                    setattr(self, key, resolved)
        self._loaded = True

    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class DatabaseConfig(BaseSettings):
    """Database connection configuration - loads from config/database.yaml."""
    
    _config_path: Path = Path("config/database.yaml")
    _loaded: bool = False

    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "postgres"
    name: str = "ai_media_factory"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_from_yaml()

    def _load_from_yaml(self):
        """Load configuration from YAML file."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                config = yaml.safe_load(f)
            for key, value in config.items():
                resolved = _resolve_env_var(value)
                if hasattr(self, key):
                    setattr(self, key, resolved)
        self._loaded = True

    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class StorageConfig(BaseSettings):
    """Storage configuration."""
    root: Path = Path("./storage")


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
    storage_root: Path = Path("./storage")
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    celery_queues: tuple = ("tts", "media", "render", "compose")
    open_api_base: str = ""
    open_api_key: str = ""

    redis: RedisConfig = RedisConfig()
    database: DatabaseConfig = DatabaseConfig()
    storage: StorageConfig = StorageConfig()
    llm_config: ModelConfig = ModelConfig()

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def redis_url(self) -> str:
        return self.redis.url

    @property
    def database_url(self) -> str:
        return self.database.async_url

    @property
    def database_url_sync(self) -> str:
        return self.database.sync_url


settings = Settings()
