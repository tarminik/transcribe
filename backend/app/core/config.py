from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        protected_namespaces=(),
    )

    env: Literal["local", "prod", "test"] = Field(default="local", alias="ENV")
    debug: bool = Field(default=True, alias="DEBUG")

    db_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/transcribe",
        alias="DATABASE_URL",
    )

    jwt_secret_key: str = Field(
        default="secret-key-change-me",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    assemblyai_api_key: str = Field(default="assemblyai-api-key", alias="ASSEMBLYAI_API_KEY")

    s3_endpoint: HttpUrl | None = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_access_key: str = Field(default="change-me", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="change-me", alias="S3_SECRET_KEY")
    s3_region: str | None = Field(default=None, alias="S3_REGION")
    s3_bucket_uploads: str = Field(default="transcribe-uploads", alias="S3_BUCKET_UPLOADS")

    max_parallel_transcriptions: int = Field(default=3, alias="MAX_PARALLEL_TRANSCRIPTIONS")
    assemblyai_tls_retries: int = Field(default=3, alias="ASSEMBLYAI_TLS_RETRIES")
    assemblyai_presigned_ttl: int = Field(default=3600, alias="ASSEMBLYAI_PRESIGNED_TTL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
