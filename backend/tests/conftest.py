import importlib
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.db.base import Base
from app.db import session as db_session
from app.services import storage as storage_service
from app.services.transcription import TranscriptionService
from app.tasks.runner import TranscriptionRunner


class DummyStorage(storage_service.StorageService):
    def __init__(self) -> None:  # type: ignore[super-init-not-called]
        self.settings = get_settings()
        self.bucket = "dummy"

    def generate_upload_key(self, user_id: str, filename: str) -> str:  # type: ignore[override]
        return f"uploads/{user_id}/{filename}"

    def generate_result_key(  # type: ignore[override]
        self,
        user_id: str,
        job_id: str,
        original_filename: str,
        extension: str = ".txt",
    ) -> str:
        ext = extension if extension.startswith(".") else f".{extension}"
        stem = Path(original_filename).stem or "transcript"
        return f"results/{user_id}/{job_id}/{stem}{ext}"

    def create_presigned_put(self, key: str, content_type: str, expires_in: int = 900) -> str:  # type: ignore[override]
        return f"https://example.com/put/{key}"

    def create_presigned_get(self, key: str, expires_in: int = 900) -> str:  # type: ignore[override]
        return f"https://example.com/get/{key}"

    async def download_to_path(self, key, destination):  # type: ignore[override]
        raise NotImplementedError

    async def upload_text(self, key, content):  # type: ignore[override]
        raise NotImplementedError

    async def delete_object(self, key):  # type: ignore[override]
        return None


@pytest.fixture(scope="session", autouse=True)
def configure_environment():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
    os.environ["JWT_SECRET_KEY"] = "test-secret"
    os.environ["ASSEMBLYAI_API_KEY"] = "test-key"
    os.environ["S3_ACCESS_KEY"] = "test"
    os.environ["S3_SECRET_KEY"] = "test"
    os.environ["S3_BUCKET_UPLOADS"] = "test-bucket"
    os.environ["STORAGE_BACKEND"] = "local"
    os.environ["TRANSCRIPTION_BACKEND"] = "stub"
    get_settings.cache_clear()
    db_session.reset_session_factory()
    storage_service.reset_storage_service()
    storage_service._storage_service = DummyStorage()


@pytest.fixture(scope="session")
def app_instance(configure_environment):
    from app import main as app_module

    importlib.reload(app_module)
    app = app_module.app

    # Setup state for tests, mimicking lifespan events
    runner = TranscriptionRunner()
    transcription_service = TranscriptionService(runner)
    app.state.transcription_runner = runner
    app.state.transcription_service = transcription_service

    app.state.transcription_runner.submit = lambda coro_factory: None  # type: ignore[attr-defined]
    app.state.transcription_service.storage = storage_service._storage_service  # type: ignore[attr-defined]
    return app


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database(app_instance):
    engine = db_session.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(app_instance):
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
