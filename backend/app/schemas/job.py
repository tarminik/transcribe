from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.transcription_job import TranscriptionStatus


class TranscriptionJobCreate(BaseModel):
    object_key: str = Field(..., min_length=1)
    language: str = Field(default="en", min_length=2, max_length=10)
    mode: Literal["mono", "dialogue"] = "mono"


class TranscriptionJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: TranscriptionStatus
    language: str
    mode: str
    result_object_key: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
