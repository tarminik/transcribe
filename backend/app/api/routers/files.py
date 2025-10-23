from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_user
from app.models import User
from app.schemas import PresignRequest, PresignResponse
from app.services.storage import LocalStorageService, get_storage_service

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/presign", response_model=PresignResponse)
async def presign_upload(
    payload: PresignRequest,
    request: Request,
    user: User = Depends(get_current_user),
) -> PresignResponse:
    storage = get_storage_service()
    object_key = storage.generate_upload_key(user.id, payload.filename)
    try:
        upload_url = storage.create_presigned_put(object_key, payload.content_type)
    except Exception as exc:  # pragma: no cover - surfaces as HTTP 500
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from exc

    if upload_url.startswith("local://upload/"):
        local_key = unquote(upload_url.removeprefix("local://upload/"))
        upload_url = str(request.url_for("upload_file", object_path=local_key))
    return PresignResponse(upload_url=upload_url, object_key=object_key)


@router.put("/upload/{object_path:path}", name="upload_file")
async def upload_file(
    object_path: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    storage = get_storage_service()
    if not isinstance(storage, LocalStorageService):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if not object_path.startswith(f"uploads/{user.id}/"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid object key")

    data = await request.body()
    await storage.save_upload(object_path, data)
    return {"object_key": object_path}


@router.get("/download/{object_path:path}", name="download_file")
async def download_file(
    object_path: str,
    user: User = Depends(get_current_user),
):
    storage = get_storage_service()
    if not isinstance(storage, LocalStorageService):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if not object_path.startswith(f"results/{user.id}/"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid object key")

    try:
        path = storage.open_for_download(object_path)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from None
    return FileResponse(path)
