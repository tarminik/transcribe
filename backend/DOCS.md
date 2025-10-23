# Transcribe SaaS Backend Notes

## Vision
- SaaS service for audio/video transcription backed by AssemblyAI.
- Initial release targets core experience: email/password accounts, unlimited usage, upload media, choose language & mono/dialogue mode, request transcription, download resulting TXT.
- Hosted on Yandex Cloud; frontend planned later.

## High-Level Architecture
- **FastAPI application** (Uvicorn) provides REST endpoints for auth, file management, and transcription job control.
- **PostgreSQL** stores users, transcription jobs, transcripts, and auth tokens (if needed).
- **AssemblyAI SDK** handles ASR; configuration toggles diarization based on mono/dialogue mode.
- **Object Storage** (Yandex Object Storage in prod, MinIO locally) keeps uploaded media and generated TXT outputs. Clients upload/download via presigned URLs.
- **Async background tasks** (within FastAPI event loop) execute transcription logic without external queue.
- **Startup recovery** scans for unfinished jobs and restarts them to mitigate single-process task handling risks.

## Key Components
- `app/main.py`: FastAPI factory, router registration, startup/shutdown hooks.
- `app/core/`: settings (Pydantic BaseSettings with env switching), logging helpers, security utilities (JWT, password hashing).
- `app/db/`: SQLAlchemy engine/session management, Alembic migrations.
- `app/models/`: SQLAlchemy ORM models (`User`, `TranscriptionJob`, `Transcript`).
- `app/schemas/`: Pydantic request/response schemas aligned with REST APIs.
- `app/services/`:
  - `auth.py`: registration, login, token issuance.
  - `storage.py`: S3-compatible presign/upload/download helpers.
  - `transcription.py`: job orchestration, AssemblyAI integration, status updates.
- `app/api/routers/`: FastAPI routers for auth, files, jobs.
- `app/tasks/`: async job runner, semaphore management, startup recovery routine.

## Data Model (initial)
- `users`: `id`, `email` (unique), `password_hash`, `created_at`.
- `transcription_jobs`: `id`, `user_id`, `status` (`pending`, `processing`, `completed`, `failed`), `language`, `mode`, `source_object_key`, `result_object_key`, `provider_job_id`, `error_message`, timestamps.
- `transcripts`: `job_id`, `plain_text`, `diarized_json` (optional), timestamps.
- Optional: `refresh_tokens` table if refresh-token flow is added.

## Core Flows
1. **Authentication**: Register, login, obtain JWT (short-lived). `/auth/register`, `/auth/login`, `/auth/me`.
2. **File Upload**:
   - Client requests `/files/presign` with filename, size, MIME.
   - Server returns presigned PUT URL and storage key.
   - Client uploads directly to object storage, then calls `/files/complete` (if needed) to confirm.
3. **Create Transcription Job**:
   - `POST /jobs` with storage key, language, mode.
   - Server stores job (`pending`), launches `asyncio.create_task(transcribe_job(job_id))`.
4. **Background Transcription**:
   - Task downloads media (stream to disk/temp), invokes AssemblyAI with diarization configurable.
   - Polls until `completed` or `error`.
   - Writes TXT transcript to storage (and/or DB), updates job status accordingly.
5. **Result Retrieval**:
   - Poll `GET /jobs` or `GET /jobs/{id}`.
   - Download TXT via `GET /jobs/{id}/download` returning signed URL.

## Async Task Strategy (Without Redis)
- Use `asyncio.create_task` when job created.
- Maintain semaphore to avoid too many concurrent transcriptions.
- On app startup, query DB for jobs in `pending`/`processing`, restart tasks.
- Handle graceful shutdown by waiting for tasks to finish (if possible).

## Local Development
- `docker-compose.yml` runs Postgres + MinIO (S3-compatible). Optionally add mailhog later.
- FastAPI runs locally with `uvicorn app.main:app --reload`.
- AssemblyAI real API key required; consider mock fixtures for tests to avoid hitting API.
- Alembic migrations manage schema; `alembic upgrade head` after changes.
- Tests via `pytest` + `httpx.AsyncClient` with dependency overrides and mocked AssemblyAI/storage.

### Local-Only Mode (without S3/AssemblyAI)
- Set `STORAGE_BACKEND=local` and `TRANSCRIPTION_BACKEND=stub` in `.env` (see `.env.example`).
- Uploaded files are stored under `LOCAL_STORAGE_DIR` on disk; presign calls return FastAPI routes for uploads/downloads.
- Use `PUT` on the provided `/files/upload/{object_key}` URL with an authenticated request to upload binaries directly.
- The stub transcriber treats uploaded UTF-8 `.txt` files as transcripts; other formats return an explanatory placeholder string.

## Deployment Targets (Yandex Cloud)
- FastAPI container on Yandex Cloud (Serverless Containers or Compute VM).
- Yandex Managed PostgreSQL for database.
- Yandex Object Storage bucket for media/results.
- Secrets (DB URL, AssemblyAI API key, storage credentials) managed via Yandex Lockbox/Secrets Manager.
- HTTPS termination via Yandex Application Load Balancer or managed ingress.

## Immediate Implementation Plan
1. Initialize project structure (`app/` modules, `requirements.txt` or Poetry).
2. Implement configuration, logging, database session factory, Alembic setup.
3. Create models and initial migration (`users`, `transcription_jobs`, `transcripts`).
4. Build auth service & router (registration/login/me) with JWT + password hashing.
5. Implement storage service for presigned uploads/downloads (MinIO/Yandex compatible). Add `/files/presign`.
6. Add transcription service, job creation router, async task + AssemblyAI integration, startup recovery.
7. Provide TXT download endpoint using presigned URLs.
8. Write core tests covering auth flow and mocked transcription pipeline.
9. Document `.env` sample and local run instructions in README (future step).

## Open Questions / Future Enhancements
- Email verification and password reset flows.
- Usage tracking/quota enforcement for future billing.
- Websocket notifications vs. polling.
- Admin interface for monitoring jobs and reviewing errors.
