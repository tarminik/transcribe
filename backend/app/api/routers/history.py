from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas import HistoryDetail, HistoryListItem
from app.services import history as history_service

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/", response_model=list[HistoryListItem])
async def list_history(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[HistoryListItem]:
    entries = await history_service.list_history_for_user(session, user.id)
    return [HistoryListItem.model_validate(entry) for entry in entries]


@router.get("/{history_id}", response_model=HistoryDetail)
async def get_history_entry(
    history_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HistoryDetail:
    entry = await history_service.get_history_entry(session, user.id, history_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    transcript = entry.job.transcript
    if transcript is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript missing")

    return HistoryDetail.model_validate(
        {
            "id": entry.id,
            "job_id": entry.job_id,
            "title": entry.title,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "transcript_text": transcript.plain_text,
        }
    )
