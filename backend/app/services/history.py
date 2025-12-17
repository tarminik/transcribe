from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import TranscriptionHistory, TranscriptionJob


async def list_history_for_user(
    session: AsyncSession, user_id: str
) -> list[TranscriptionHistory]:
    stmt = (
        select(TranscriptionHistory)
        .where(TranscriptionHistory.user_id == user_id)
        .order_by(TranscriptionHistory.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_history_entry(
    session: AsyncSession, user_id: str, history_id: str
) -> TranscriptionHistory | None:
    stmt = (
        select(TranscriptionHistory)
        .options(
            selectinload(TranscriptionHistory.job).selectinload(
                TranscriptionJob.transcript
            )
        )
        .where(
            TranscriptionHistory.id == history_id,
            TranscriptionHistory.user_id == user_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
