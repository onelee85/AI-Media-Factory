"""FastAPI endpoint for serving the Remotion preview player.

Serves the player HTML, static assets, and a data endpoint
that returns composition props for a given script/project.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.db import async_session
from app.models.audio import AudioFile
from app.models.subtitle import Subtitle
from app.storage import StorageService
from sqlalchemy import select

preview_router = APIRouter(prefix="/preview", tags=["preview"])

PLAYER_DIR = Path(__file__).resolve().parents[2] / "remotion" / "player"
STORAGE = StorageService()


@preview_router.get("/", response_class=HTMLResponse)
async def preview_index():
    """Serve the preview player HTML."""
    index_html = PLAYER_DIR / "index.html"
    if not index_html.exists():
        raise HTTPException(status_code=404, detail="Preview player not found")
    return FileResponse(index_html)


@preview_router.get("/data/{audio_id}")
async def preview_data(audio_id: str):
    """Return composition props JSON for a given audio_id.

    Loads AudioFile + latest SRT Subtitle from DB and constructs
    the props dict expected by the VideoComposition component.
    """
    async with async_session() as session:
        # Fetch audio
        result = await session.execute(
            select(AudioFile).where(AudioFile.id == audio_id)
        )
        audio = result.scalar_one_or_none()
        if not audio:
            raise HTTPException(status_code=404, detail=f"Audio {audio_id} not found")

        # Fetch latest SRT subtitle for this audio
        result = await session.execute(
            select(Subtitle)
            .where(Subtitle.audio_id == audio_id, Subtitle.format == "srt")
            .order_by(Subtitle.created_at.desc())
            .limit(1)
        )
        subtitle = result.scalar_one_or_none()

        subtitle_text = ""
        if subtitle and subtitle.status == "completed":
            subtitle_text = subtitle.content or ""

        # Construct audio URL (relative path served via media mount)
        audio_url = f"/preview/media/audio/{audio.file_path}" if audio.file_path else ""

        return {
            "audioSrc": audio_url,
            "subtitleText": subtitle_text,
            "backgroundImages": [],
            "titleText": "",
            "fps": 30,
            "width": 1920,
            "height": 1080,
        }


# Mount static files for player assets (JS/CSS)
if PLAYER_DIR.exists():
    preview_router.mount("/assets", StaticFiles(directory=str(PLAYER_DIR)), name="player-assets")

# Mount storage assets for media files (audio, images)
assets_root = STORAGE.root / "assets"
if assets_root.exists():
    preview_router.mount("/media", StaticFiles(directory=str(assets_root)), name="media-assets")
