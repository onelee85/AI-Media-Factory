#!/usr/bin/env python3
"""Single-command development bootstrap script."""

import asyncio
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def init_db():
    """Initialize database tables."""
    from app.db import init_db
    await init_db()
    print("[✓] Database tables created")


def check_ffmpeg():
    """Validate FFmpeg is available."""
    from app.ffmpeg_utils import check_ffmpeg, FFmpegError
    try:
        result = check_ffmpeg()
        print(f"[✓] FFmpeg available: {result.get('version', 'unknown')}")
    except FFmpegError as e:
        print(f"[!] FFmpeg warning: {e}")


def main():
    print("=" * 50)
    print("AI-Media-Factory Dev Bootstrap")
    print("=" * 50)

    print("\n[1/4] Starting Docker services...")
    subprocess.run(["docker", "compose", "up", "-d"], check=True)
    print("[✓] Docker services started")

    print("\n[2/4] Waiting for services to initialize...")
    time.sleep(5)

    print("\n[3/4] Initializing database...")
    asyncio.run(init_db())

    print("\n[4/4] Checking FFmpeg...")
    check_ffmpeg()

    print("\n" + "=" * 50)
    print("Starting application services...")
    print("=" * 50)

    processes = []

    def handle_interrupt(signum, frame):
        print("\n[✗] Shutting down...")
        for p in processes:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_interrupt)

    print("\n[API] Starting uvicorn on port 8000...")
    api_process = subprocess.Popen(
        [
            "uvicorn", "app.main:app",
            "--reload", "--host", "0.0.0.0", "--port", "8000",
        ],
        cwd=Path(__file__).parent.parent,
    )
    processes.append(api_process)

    print("[Celery] Starting Celery worker...")
    celery_process = subprocess.Popen(
        [
            "celery", "-A", "app.celery_app", "worker",
            "-Q", "tts,media,render,compose",
            "--concurrency", "2",
        ],
        cwd=Path(__file__).parent.parent,
    )
    processes.append(celery_process)

    print("\n" + "=" * 50)
    print("Services are ready!")
    print("=" * 50)
    print("API:        http://localhost:8000")
    print("Health:     http://localhost:8000/api/health")
    print("Docs:       http://localhost:8000/docs")
    print("=" * 50)
    print("\nPress Ctrl+C to stop all services")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle_interrupt(None, None)


if __name__ == "__main__":
    main()