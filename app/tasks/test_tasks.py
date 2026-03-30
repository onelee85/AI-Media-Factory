import time
from app.celery_app import celery_app


@celery_app.task(bind=True, name="app.tasks.tts.test_task")
def tts_test_task(self):
    time.sleep(1)
    return {"queue": "tts", "message": "TTS test task completed"}


@celery_app.task(bind=True, name="app.tasks.media.test_task")
def media_test_task(self):
    time.sleep(1)
    return {"queue": "media", "message": "Media test task completed"}


@celery_app.task(bind=True, name="app.tasks.render.test_task")
def render_test_task(self):
    time.sleep(1)
    return {"queue": "render", "message": "Render test task completed"}


@celery_app.task(bind=True, name="app.tasks.compose.test_task")
def compose_test_task(self):
    time.sleep(1)
    return {"queue": "compose", "message": "Compose test task completed"}
