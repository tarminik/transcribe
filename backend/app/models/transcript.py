from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Transcript(Base):
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transcriptionjob.id", ondelete="CASCADE"),
        primary_key=True,
    )
    plain_text: Mapped[str] = mapped_column(Text, nullable=False)
    diarized_json: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    job: Mapped["TranscriptionJob"] = relationship(
        "TranscriptionJob",
        back_populates="transcript",
    )
