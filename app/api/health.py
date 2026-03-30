import litellm
from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.db import async_session
from app.ffmpeg_utils import check_ffmpeg, FFmpegError
from app.services import ModelProviderService

health_router = APIRouter(prefix="/api/health", tags=["health"])


@health_router.get("")
async def health_check():
    redis_status = await _check_redis()
    postgres_status = await _check_postgres()
    ffmpeg_status = _check_ffmpeg()
    model_status = await check_model_health()

    all_ok = (
        redis_status["status"] == "ok"
        and postgres_status["status"] == "ok"
        and ffmpeg_status["status"] == "ok"
        and all(v["status"] == "ok" for v in model_status.values())
    )

    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": {
            "redis": redis_status,
            "postgres": postgres_status,
            "ffmpeg": ffmpeg_status,
            "models": model_status,
        },
    }


async def check_model_health() -> dict:
    """Check if configured LLM providers are reachable"""
    service = ModelProviderService()
    results = {}

    for name, config in service.config.providers.items():
        try:
            response = litellm.completion(
                model=config.model,
                messages=[{"role": "user", "content": "hi"}],
                base_url=config.base_url,
                api_key=config.api_key,
                timeout=10,
            )
            results[name] = {"status": "ok", "model": config.model}
        except Exception as e:
            results[name] = {"status": "error", "error": str(e)}

    return results


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