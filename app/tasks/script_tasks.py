import traceback
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.db import async_session
from app.models.script import Script
from app.services.script_generator import script_generator_service, ScriptGeneratorService
from app.services.model_provider import ModelProviderError
from sqlalchemy import select


@celery_app.task(bind=True, name="app.tasks.scripts.generate", acks_late=True)
def generate_script_task(
    self,
    script_id: str,
    prompt: str,
    provider: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
):
    """
    Celery task: generate a video script using LLM and persist the result.

    Updates the Script record status through its lifecycle:
      queued -> generating -> completed / failed
    """
    import asyncio

    return asyncio.run(
        _generate_script_async(
            script_id=script_id,
            prompt=prompt,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
            task_instance=self,
        )
    )


async def _generate_script_async(
    script_id: str,
    prompt: str,
    provider: str | None,
    temperature: float,
    max_tokens: int,
    task_instance,
):
    """Async core of the script generation task."""
    async with async_session() as session:
        # Fetch the script record
        result = await session.execute(
            select(Script).where(Script.id == script_id)
        )
        script = result.scalar_one_or_none()
        if not script:
            return {"error": f"Script {script_id} not found"}

        # Mark as generating
        script.status = "generating"
        await session.flush()

        try:
            generation_result = script_generator_service.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                provider=provider,
            )

            # Build the script content from the structured result
            content = _format_script_content(generation_result)

            script.content = content
            script.title = generation_result.get("title", script.title)
            script.model = generation_result.get("model", "")
            script.status = "completed"
            script.completed_at = datetime.now(timezone.utc)
            script.metadata = {
                **(script.metadata or {}),
                "sections": generation_result.get("sections", []),
                "summary": generation_result.get("summary", ""),
                "usage": generation_result.get("usage", {}),
                "provider_used": generation_result.get("provider", ""),
            }
            await session.flush()

            return {
                "script_id": script_id,
                "status": "completed",
                "title": script.title,
            }

        except (ModelProviderError, ValueError) as exc:
            script.status = "failed"
            script.error = str(exc)
            await session.flush()
            return {"script_id": script_id, "status": "failed", "error": str(exc)}

        except Exception as exc:
            script.status = "failed"
            script.error = f"{type(exc).__name__}: {exc}"
            await session.flush()
            raise


def _format_script_content(result: dict) -> str:
    """Convert structured script JSON to human-readable markdown."""
    lines = [f"# {result.get('title', 'Untitled Script')}", ""]

    for section in result.get("sections", []):
        heading = section.get("heading", "Section")
        content = section.get("content", "")
        duration = section.get("duration_estimate_sec")
        duration_str = f" (~{duration}s)" if duration else ""
        lines.append(f"## {heading}{duration_str}")
        lines.append("")
        lines.append(content)
        lines.append("")

    summary = result.get("summary", "")
    if summary:
        lines.append("---")
        lines.append(f"**Summary:** {summary}")

    return "\n".join(lines)
