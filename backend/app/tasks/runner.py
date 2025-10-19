import asyncio
import logging
from typing import Awaitable, Callable

from app.core.config import get_settings

logger = logging.getLogger(__name__)


StartupHook = Callable[[], Awaitable[None]]
CoroFactory = Callable[[], Awaitable[None]]


class TranscriptionRunner:
    """Coordinates background transcription tasks within the FastAPI process."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._tasks: set[asyncio.Task] = set()
        self._running = False
        self._semaphore: asyncio.Semaphore | None = None
        self._startup_hook: StartupHook | None = None

    def set_startup_hook(self, hook: StartupHook) -> None:
        self._startup_hook = hook

    async def start(self) -> None:
        if self._running:
            return
        self._loop = asyncio.get_running_loop()
        settings = get_settings()
        self._semaphore = asyncio.Semaphore(settings.max_parallel_transcriptions)
        self._running = True
        if self._startup_hook:
            await self._startup_hook()

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._semaphore = None
        self._loop = None

    def submit(self, coro_factory: CoroFactory) -> None:
        if not self._running or self._loop is None or self._semaphore is None:
            raise RuntimeError("TranscriptionRunner not running")

        async def wrapper() -> None:
            async with self._semaphore:
                try:
                    await coro_factory()
                except asyncio.CancelledError:
                    raise
                except Exception:  # pragma: no cover - logged for observability
                    logger.exception("Unhandled error in transcription task")

        task = self._loop.create_task(wrapper())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
