from pydantic import BaseModel, Field


class PresignRequest(BaseModel):
    filename: str = Field(..., min_length=1)
    content_type: str = Field(default="application/octet-stream")


class PresignResponse(BaseModel):
    upload_url: str
    object_key: str


class DownloadResponse(BaseModel):
    download_url: str
    object_key: str
