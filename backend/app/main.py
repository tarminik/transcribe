from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import get_settings
from app.services.transcription import TranscriptionService
from app.tasks.runner import TranscriptionRunner
from app.api.routers import auth as auth_router
from app.api.routers import files as files_router
from app.api.routers import history as history_router
from app.api.routers import jobs as jobs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    runner = TranscriptionRunner()
    transcription_service = TranscriptionService(runner)
    app.state.transcription_service = transcription_service

    await runner.start()
    yield
    await runner.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        debug=settings.debug,
        title="Transcribe SaaS API",
        lifespan=lifespan,
    )

    app.include_router(auth_router.router)
    app.include_router(files_router.router)
    app.include_router(history_router.router)
    app.include_router(jobs_router.router)

    return app


app = create_app()
