import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.script import Script
from app.tasks.script_tasks import generate_script_task

scripts_router = APIRouter(prefix="/api/scripts", tags=["scripts"])


# --- Request / Response schemas ---


class ScriptCreateRequest(BaseModel):
    project_id: uuid.UUID
    prompt: str = Field(..., min_length=1, max_length=4000, description="Topic or brief for the script")
    title: str = Field(default="Untitled Script", max_length=300)
    provider: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=100, le=8000)


class ScriptResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    celery_task_id: str | None
    title: str
    content: str | None
    prompt: str
    provider: str | None
    model: str | None
    status: str
    script_metadata: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


# --- Endpoints ---


@scripts_router.post("", response_model=ScriptResponse, status_code=201)
async def create_script(
    body: ScriptCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Queue a new script generation task via Celery."""
    script = Script(
        project_id=body.project_id,
        title=body.title,
        prompt=body.prompt,
        provider=body.provider,
        status="pending",
        script_metadata={"temperature": body.temperature, "max_tokens": body.max_tokens},
    )
    db.add(script)
    await db.flush()

    # Dispatch async Celery task
    celery_result = generate_script_task.delay(
        script_id=str(script.id),
        prompt=body.prompt,
        provider=body.provider,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )

    script.celery_task_id = celery_result.id
    script.status = "queued"
    await db.flush()
    await db.refresh(script)

    return script


@scripts_router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single script by ID."""
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@scripts_router.get("", response_model=list[ScriptResponse])
async def list_scripts(
    project_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List scripts, optionally filtered by project or status."""
    query = select(Script).order_by(Script.created_at.desc())
    if project_id is not None:
        query = query.where(Script.project_id == project_id)
    if status is not None:
        query = query.where(Script.status == status)
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


@scripts_router.delete("/{script_id}", status_code=204)
async def delete_script(
    script_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a script."""
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    await db.delete(script)
