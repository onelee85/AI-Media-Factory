from celery import Celery
from app.config import settings

celery_app = Celery("ai_media_factory")
celery_app.config_from_object({
    "broker_url": settings.redis_url,
    "result_backend": settings.redis_url,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "timezone": "UTC",
    "enable_utc": True,
    "task_routes": {
        "app.tasks.tts.*": {"queue": "tts"},
        "app.tasks.media.*": {"queue": "media"},
        "app.tasks.render.*": {"queue": "render"},
        "app.tasks.compose.*": {"queue": "compose"},
        "app.tasks.scripts.*": {"queue": "scripts"},
        "app.tasks.pipeline.generate_video": {"queue": "scripts"},
    },
    "task_time_limit": 1800,
    "task_soft_time_limit": 1500,
    "queues": ["celery", "scripts", "tts", "media", "render", "compose"],
})
celery_app.autodiscover_tasks(["app.tasks"])