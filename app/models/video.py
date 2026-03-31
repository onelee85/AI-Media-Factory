import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    script_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scripts.id"), nullable=False
    )
    audio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_files.id"), nullable=False
    )
    subtitle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subtitles.id"), nullable=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int] = mapped_column(nullable=False, default=1920)
    height: Mapped[int] = mapped_column(nullable=False, default=1080)
    codec: Mapped[str] = mapped_column(String(50), nullable=False, default="h264")
    render_props: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
