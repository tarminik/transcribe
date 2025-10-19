import asyncio
import re
from pathlib import Path
from uuid import uuid4

import boto3
from botocore.client import Config

from app.core.config import get_settings


def _sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name or "file"


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        session = boto3.session.Session()
        self.client = session.client(
            "s3",
            endpoint_url=str(self.settings.s3_endpoint) if self.settings.s3_endpoint else None,
            aws_access_key_id=self.settings.s3_access_key,
            aws_secret_access_key=self.settings.s3_secret_key,
            region_name=self.settings.s3_region,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = self.settings.s3_bucket_uploads

    def generate_upload_key(self, user_id: str, filename: str) -> str:
        safe_name = _sanitize_filename(filename)
        return f"uploads/{user_id}/{uuid4()}_{safe_name}"

    def generate_result_key(self, user_id: str, job_id: str, extension: str = ".txt") -> str:
        ext = extension if extension.startswith(".") else f".{extension}"
        return f"results/{user_id}/{job_id}{ext}"

    def create_presigned_put(
        self,
        key: str,
        content_type: str,
        expires_in: int = 900,
    ) -> str:
        return self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )

    def create_presigned_get(self, key: str, expires_in: int = 900) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    async def download_to_path(self, key: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)

        def _download() -> None:
            with destination.open("wb") as f:
                self.client.download_fileobj(self.bucket, key, f)

        await asyncio.to_thread(_download)

    async def upload_text(self, key: str, content: str) -> None:

        data = content.encode("utf-8")

        def _upload() -> None:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType="text/plain; charset=utf-8",
            )

        await asyncio.to_thread(_upload)


_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
