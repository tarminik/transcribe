from __future__ import annotations

import asyncio
import json
import logging
import ssl
from datetime import datetime, timezone
from pathlib import Path

import assemblyai as aai
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.models import (
    Transcript,
    TranscriptionHistory,
    TranscriptionJob,
    TranscriptionStatus,
    User,
)
from app.schemas import TranscriptionJobCreate
from app.services.storage import StorageService, get_storage_service
from app.tasks.runner import TranscriptionRunner

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(
        self, runner: TranscriptionRunner, storage: StorageService | None = None
    ) -> None:
        self.settings = get_settings()
        aai.settings.api_key = self.settings.assemblyai_api_key
        self.runner = runner
        self.storage = storage or get_storage_service()
        self._session_factory: async_sessionmaker[AsyncSession] = get_session_factory()
        self.runner.set_startup_hook(self._recover_pending_jobs)

    def _history_title_from_source(self, source_object_key: str) -> str | None:
        name = Path(source_object_key).name
        if "_" in name:
            _, remainder = name.split("_", 1)
            candidate = remainder or name
        else:
            candidate = name

        cleaned = candidate.strip()
        return cleaned or None

    async def create_job(
        self,
        session: AsyncSession,
        user: User,
        payload: TranscriptionJobCreate,
    ) -> TranscriptionJob:
        job = TranscriptionJob(
            user_id=user.id,
            language=payload.language,
            mode=payload.mode,
            source_object_key=payload.object_key,
            status=TranscriptionStatus.PENDING,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

        try:
            self.runner.submit(lambda: self._process_job(job.id))
        except RuntimeError:
            logger.warning(
                "Transcription runner not ready; job %s left pending", job.id
            )
        return job

    async def _recover_pending_jobs(self) -> None:
        async with self._session_factory() as session:
            stmt = select(TranscriptionJob.id).where(
                TranscriptionJob.status.in_(
                    [TranscriptionStatus.PENDING, TranscriptionStatus.PROCESSING]
                )
            )
            result = await session.execute(stmt)
            job_ids = [row[0] for row in result.all()]

        if job_ids:
            logger.info("Recovering %d pending transcription jobs", len(job_ids))
        for job_id in job_ids:
            try:
                self.runner.submit(lambda job_id=job_id: self._process_job(job_id))
            except RuntimeError:
                logger.error("Runner not available to recover job %s", job_id)

    async def _process_job(self, job_id: str) -> None:
        source_key: str | None = None
        async with self._session_factory() as session:
            job = await session.get(
                TranscriptionJob,
                job_id,
                options=[selectinload(TranscriptionJob.transcript)],
            )
            if not job:
                logger.warning("Job %s not found", job_id)
                return

            if job.status == TranscriptionStatus.COMPLETED:
                logger.info("Job %s already completed", job_id)
                return

            source_key = job.source_object_key
            job.status = TranscriptionStatus.PROCESSING
            job.error_message = None
            job.updated_at = datetime.now(timezone.utc)
            await session.commit()

        try:
            transcript_text, diarized_json = await self._run_transcription(job_id)
        except Exception as exc:
            logger.exception("Transcription job %s failed", job_id)
            async with self._session_factory() as session:
                job = await session.get(TranscriptionJob, job_id)
                if job:
                    job.status = TranscriptionStatus.FAILED
                    job.error_message = str(exc)
                    job.updated_at = datetime.now(timezone.utc)
                    await session.commit()
            if source_key:
                await self._delete_source_object(source_key, job_id)
            return

        # Persist results
        async with self._session_factory() as session:
            job = await session.get(
                TranscriptionJob,
                job_id,
                options=[selectinload(TranscriptionJob.transcript)],
            )
            if not job:
                logger.warning("Job %s missing when saving results", job_id)
                return

        result_key = self.storage.generate_result_key(job.user_id, job.id)
        await self.storage.upload_text(result_key, transcript_text)

        async with self._session_factory() as session:
            job = await session.get(
                TranscriptionJob,
                job_id,
                options=[selectinload(TranscriptionJob.transcript)],
            )
            if not job:
                logger.warning("Job %s missing during final save", job_id)
                return

            job.status = TranscriptionStatus.COMPLETED
            job.result_object_key = result_key
            job.updated_at = datetime.now(timezone.utc)

            transcript = job.transcript
            if transcript is None:
                transcript = Transcript(
                    job_id=job.id,
                    plain_text=transcript_text,
                    diarized_json=diarized_json,
                )
                session.add(transcript)
            else:
                transcript.plain_text = transcript_text
                transcript.diarized_json = diarized_json
                transcript.updated_at = datetime.now(timezone.utc)

            history_entry = job.history_entry
            if history_entry is None:
                history_entry = TranscriptionHistory(
                    user_id=job.user_id,
                    job_id=job.id,
                    title=self._history_title_from_source(job.source_object_key),
                )
                session.add(history_entry)
            else:
                if not history_entry.title:
                    history_entry.title = self._history_title_from_source(
                        job.source_object_key
                    )
                history_entry.updated_at = datetime.now(timezone.utc)

            await session.commit()

        if source_key:
            await self._delete_source_object(source_key, job_id)

    async def _run_transcription(self, job_id: str) -> tuple[str, str | None]:
        async with self._session_factory() as session:
            job = await session.get(TranscriptionJob, job_id)
            if not job:
                raise RuntimeError(f"Job {job_id} not found during execution")

            source_key = job.source_object_key
            language = job.language
            mode = job.mode

            if mode == "mono":
                speaker_labels = False  # no diarization in mono mode
                speakers_expected = None
            elif mode == "dialogue":
                speaker_labels = True
                speakers_expected = 2
            else:  # "multi"
                speaker_labels = True
                speakers_expected = None

        if language == "auto":
            config = aai.TranscriptionConfig(
                language_detection=True,
                speaker_labels=speaker_labels,
                speakers_expected=speakers_expected,
            )
        else:
            config = aai.TranscriptionConfig(
                language_code=language,
                speaker_labels=speaker_labels,
                speakers_expected=speakers_expected,
            )

        async def _transcribe_once() -> aai.Transcript:
            transcriber = aai.Transcriber()
            audio_url = self.storage.create_presigned_get(
                source_key,
                expires_in=self.settings.assemblyai_presigned_ttl,
            )

            def _run() -> aai.Transcript:
                return transcriber.transcribe(audio_url, config=config)

            return await asyncio.to_thread(_run)

        max_attempts = max(1, self.settings.assemblyai_tls_retries)
        transcript = None
        for attempt in range(1, max_attempts + 1):
            try:
                transcript = await _transcribe_once()
                break
            except (httpx.ConnectError, ssl.SSLCertVerificationError) as exc:
                message = str(exc)
                is_hostname_issue = "certificate verify failed" in message.lower()
                if attempt >= max_attempts or not is_hostname_issue:
                    raise
                wait_seconds = min(2**attempt, 10)
                logger.warning(
                    "AssemblyAI TLS handshake failed for job %s (attempt %d/%d): %s. Retrying in %ss",
                    job_id,
                    attempt,
                    max_attempts,
                    message,
                    wait_seconds,
                )
                await asyncio.sleep(wait_seconds)
            except Exception:
                # Any non-TLS failure should surface immediately.
                raise

        if transcript is None:
            raise RuntimeError(
                "AssemblyAI transcription did not return a result after retries"
            )

        if transcript.status == "error":
            raise RuntimeError(transcript.error or "Transcription failed")

        text = transcript.text or ""
        diarized_json = None
        if transcript.utterances:
            diarized_json = json.dumps(
                [
                    {
                        "speaker": utterance.speaker,
                        "start": utterance.start,
                        "end": utterance.end,
                        "text": utterance.text,
                    }
                    for utterance in transcript.utterances
                ],
                ensure_ascii=False,
            )
            if speaker_labels and mode in ("dialogue", "multi"):
                # Build a speaker-labelled transcript for dialog/multi so the saved TXT is readable.
                text = "\n".join(
                    f"Speaker {utterance.speaker}: {utterance.text}"
                    for utterance in transcript.utterances
                )

        return text, diarized_json

    async def _delete_source_object(self, source_key: str, job_id: str) -> None:
        try:
            await self.storage.delete_object(source_key)
        except Exception:  # pragma: no cover - logged for observability
            logger.exception(
                "Failed to delete source object %s for job %s", source_key, job_id
            )
