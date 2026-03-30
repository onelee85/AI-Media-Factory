import shutil
import subprocess
from pathlib import Path

import ffmpeg
from redis import Redis

from app.config import settings


class FFmpegError(Exception):
    pass


def check_ffmpeg() -> dict:
    ffmpeg_path = shutil.which(settings.ffmpeg_binary)
    if not ffmpeg_path:
        raise FFmpegError("FFmpeg binary not found")

    try:
        result = subprocess.run(
            [settings.ffmpeg_binary, "-version"],
            capture_output=True,
            text=True,
            check=True,
        )
        first_line = result.stdout.split("\n")[0]
        version = first_line.split(" ")[2] if len(result.stdout.split("\n")) > 0 else "unknown"
        return {"available": True, "version": version}
    except Exception as e:
        raise FFmpegError(f"FFmpeg check failed: {e}")


def generate_test_clip(output_path: Path | str, duration: int = 5) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        stream = ffmpeg.input(
            "testsrc2=size=1920x1080:rate=30",
            f="lavfi",
            t=duration,
        )
        stream = ffmpeg.filter(stream, "format", "yuv420p")

        audio_stream = ffmpeg.input(
            "sine=frequency=440",
            f="lavfi",
            t=duration,
        )

        ffmpeg.output(
            stream,
            audio_stream,
            str(output_path),
            vcodec="libx264",
            acodec="aac",
            video_bitrate="5M",
            audio_bitrate="192k",
            pix_fmt="yuv420p",
            preset="fast",
            t=duration,
            **{"movflags": "+faststart"},
        ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)

        return output_path

    except ffmpeg.Error as e:
        raise FFmpegError(f"FFmpeg encoding failed: {e.stderr.decode() if e.stderr else str(e)}")


async def check_redis() -> dict:
    try:
        r = Redis.from_url(settings.redis_url)
        r.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_postgres(session) -> dict:
    try:
        from sqlalchemy import text
        await session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}