from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Transcript, TranscriptionJob


async def list_jobs_for_user(session: AsyncSession, user_id: str) -> list[TranscriptionJob]:
    stmt = (
        select(TranscriptionJob)
        .where(TranscriptionJob.user_id == user_id)
        .order_by(TranscriptionJob.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_job_for_user(
    session: AsyncSession,
    user_id: str,
    job_id: str,
) -> TranscriptionJob | None:
    stmt = (
        select(TranscriptionJob)
        .options(selectinload(TranscriptionJob.transcript))
        .where(TranscriptionJob.id == job_id, TranscriptionJob.user_id == user_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
