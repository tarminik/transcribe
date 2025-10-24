from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas import DownloadResponse, TranscriptionJobCreate, TranscriptionJobRead
from app.services import jobs as job_service
from app.services.storage import get_storage_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=TranscriptionJobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: TranscriptionJobCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TranscriptionJobRead:
    transcription_service = request.app.state.transcription_service
    job = await transcription_service.create_job(session, user, payload)
    return TranscriptionJobRead.model_validate(job)


@router.get("/", response_model=list[TranscriptionJobRead])
async def list_jobs(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TranscriptionJobRead]:
    jobs = await job_service.list_jobs_for_user(session, user.id)
    return [TranscriptionJobRead.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=TranscriptionJobRead)
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TranscriptionJobRead:
    job = await job_service.get_job_for_user(session, user.id, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return TranscriptionJobRead.model_validate(job)


@router.get("/{job_id}/download", response_model=DownloadResponse)
async def download_job_result(
    job_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DownloadResponse:
    job = await job_service.get_job_for_user(session, user.id, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not job.result_object_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job not completed yet")
    storage = get_storage_service()
    download_url = storage.create_presigned_get(job.result_object_key)
    if download_url.startswith("local://download/"):
        local_key = unquote(download_url.removeprefix("local://download/"))
        download_url = f"/files/download/{local_key}"
    return DownloadResponse(download_url=download_url, object_key=job.result_object_key)
