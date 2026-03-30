from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.db import async_session
from app.ffmpeg_utils import check_ffmpeg, FFmpegError

health_router = APIRouter(prefix="/api/health", tags=["health"])


@health_router.get("")
async def health_check():
    redis_status = await _check_redis()
    postgres_status = await _check_postgres()
    ffmpeg_status = _check_ffmpeg()

    all_ok = (
        redis_status["status"] == "ok"
        and postgres_status["status"] == "ok"
        and ffmpeg_status["status"] == "ok"
    )

    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": {
            "redis": redis_status,
            "postgres": postgres_status,
            "ffmpeg": ffmpeg_status,
        },
    }


async def _check_redis() -> dict:
    try:
        from redis import Redis
        r = await Redis.from_url(settings.redis_url)
        await r.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _check_postgres() -> dict:
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_ffmpeg() -> dict:
    try:
        result = check_ffmpeg()
        return {"status": "ok", "version": result.get("version")}
    except FFmpegError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}