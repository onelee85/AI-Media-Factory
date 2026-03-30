from pydantic_settings import BaseSettings
from pathlib import Path


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
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
