import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Subtitle(Base):
    __tablename__ = "subtitles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    script_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scripts.id"), nullable=False)
    audio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("audio_files.id"), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)  # "srt" or "ass"
    file_path: Mapped[str] = mapped_column(Text, nullable=False)  # Relative path in storage
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Raw subtitle file content
    word_count: Mapped[int | None] = mapped_column(nullable=True)
    line_count: Mapped[int | None] = mapped_column(nullable=True)
    sync_accuracy: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
