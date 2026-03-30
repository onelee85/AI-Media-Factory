from fastapi import FastAPI
from app.config import settings
from app.api.health import health_router

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(health_router)


@app.get("/")
async def root():
    return {"name": settings.app_name, "status": "running"}
