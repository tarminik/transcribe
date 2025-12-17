from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HistoryListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime


class HistoryDetail(HistoryListItem):
    transcript_text: str
