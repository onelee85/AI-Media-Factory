from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path

from app.config import settings
from app.api.health import health_router
from app.api.scripts import scripts_router
from app.api.preview import preview_router
from app.api.videos import videos_router

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(health_router)
app.include_router(scripts_router)
app.include_router(preview_router)
app.include_router(videos_router)

# Mount web UI static files
web_dir = Path(__file__).parent / "web"
if web_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/web", StaticFiles(directory=str(web_dir), html=True), name="web")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect root to web UI."""
    if web_dir.exists():
        return '<html><head><meta http-equiv="refresh" content="0;url=/web/"></head></html>'
    return f'<html><body><h1>{settings.app_name}</h1><p>Status: running</p></body></html>'
