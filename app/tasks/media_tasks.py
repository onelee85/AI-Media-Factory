"""Celery task for async stock media matching.

Extracts keywords from script sections, searches Pexels for matching images,
downloads them, and persists results to ScriptMedia record.
"""
import json
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.celery_app import celery_app
from app.db import async_session
from app.models.script import Script
from app.models.script_media import ScriptMedia
from app.services.media_service import (
    KeywordExtractor,
    PexelsClient,
    PexelsClientError,
    StockMediaService,
)
from app.storage import StorageService


@celery_app.task(bind=True, name="app.tasks.media.match", acks_late=True)
def match_media_task(
    self,
    script_id: str,
    images_per_section: int = 1,
):
    """Celery task: match stock images to script sections via Pexels API.

    Args:
        script_id: UUID string of Script record.
        images_per_section: Number of images to fetch per section (default 1).

    Returns:
        Dict with script_media_id, status, matched_sections count.
    """
    import asyncio

    return asyncio.run(
        _match_media_async(
            script_id=script_id,
            images_per_section=images_per_section,
            task_id=self.request.id if hasattr(self, "request") else None,
        )
    )


async def _match_media_async(
    script_id: str,
    images_per_section: int,
    task_id: str | None,
):
    """Async core of the media matching task."""
    storage = StorageService()

    # Get Pexels API key from environment
    api_key = os.getenv("PEXELS_API_KEY", "")
    if not api_key:
        return {"error": "PEXELS_API_KEY not configured"}

    pexels_client = PexelsClient(api_key=api_key)
    keyword_extractor = KeywordExtractor()
    media_service = StockMediaService(pexels_client, keyword_extractor, storage)

    try:
        async with async_session() as session:
            # Fetch script
            result = await session.execute(
                select(Script).where(Script.id == script_id)
            )
            script = result.scalar_one_or_none()
            if not script:
                return {"error": f"Script {script_id} not found"}

            if not script.content:
                return {"error": f"Script {script_id} has no content"}

            # Parse script sections from content
            try:
                script_data = json.loads(script.content)
                sections = script_data.get("sections", [])
            except (json.JSONDecodeError, TypeError):
                return {"error": f"Script {script_id} content is not valid JSON"}

            if not sections:
                return {"error": f"Script {script_id} has no sections"}

            # Create ScriptMedia record
            script_media = ScriptMedia(
                script_id=script.id,
                celery_task_id=task_id,
                status="matching",
            )
            session.add(script_media)
            await session.flush()
            media_id = str(script_media.id)

            try:
                # Set up save directory
                save_dir = storage.image_dir() / str(script_id)

                # Run matching
                section_results = media_service.match_images_to_script(
                    script_sections=sections,
                    save_dir=save_dir,
                    images_per_section=images_per_section,
                )

                # Build matched_images JSONB
                matched_images = []
                for idx, image_paths in enumerate(section_results):
                    keywords = keyword_extractor.extract_keywords(sections[idx])
                    matched_images.append(
                        {
                            "section_index": idx,
                            "image_paths": [str(p) for p in image_paths],
                            "keywords": keywords,
                        }
                    )

                # Update ScriptMedia record
                script_media.status = "completed"
                script_media.matched_images = matched_images
                script_media.completed_at = datetime.now(timezone.utc)
                await session.flush()

                total_images = sum(len(paths) for paths in section_results)

                return {
                    "script_media_id": media_id,
                    "status": "completed",
                    "matched_sections": len(sections),
                    "total_images": total_images,
                }

            except PexelsClientError as exc:
                script_media.status = "failed"
                script_media.error = str(exc)
                await session.flush()
                return {
                    "script_media_id": media_id,
                    "status": "failed",
                    "error": str(exc),
                }

            except Exception as exc:
                script_media.status = "failed"
                script_media.error = (
                    f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
                )
                await session.flush()
                return {
                    "script_media_id": media_id,
                    "status": "failed",
                    "error": str(exc),
                }
    finally:
        pexels_client.close()
