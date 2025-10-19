from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models import User
from app.schemas import PresignRequest, PresignResponse
from app.services.storage import get_storage_service

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/presign", response_model=PresignResponse)
async def presign_upload(
    payload: PresignRequest,
    user: User = Depends(get_current_user),
) -> PresignResponse:
    storage = get_storage_service()
    object_key = storage.generate_upload_key(user.id, payload.filename)
    try:
        upload_url = storage.create_presigned_put(object_key, payload.content_type)
    except Exception as exc:  # pragma: no cover - surfaces as HTTP 500
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from exc
    return PresignResponse(upload_url=upload_url, object_key=object_key)
