from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TranscriptionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptionJob(Base):
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[TranscriptionStatus] = mapped_column(
        SqlEnum(TranscriptionStatus, name="transcription_status"),
        default=TranscriptionStatus.PENDING,
        nullable=False,
    )
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # mono | dialogue
    source_object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    result_object_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    provider_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    transcript: Mapped["Transcript"] = relationship(
        "Transcript",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )


Index(
    "ix_transcription_job_user_created",
    TranscriptionJob.user_id,
    TranscriptionJob.created_at.desc(),
)
