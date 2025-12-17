# Tech: Transcribe

This document gives a high‑level technical picture for agents and humans.
For deeper backend details, see `backend/DOCS.md`.

## Stack Overview
- **Backend**: Python 3.12+, FastAPI, SQLAlchemy, Pydantic, Alembic.
- **Frontend**: React + Vite, minimal UI for auth, upload, and job tracking.
- **Database**: PostgreSQL in production; SQLite is used for local/dev by default.
- **Storage**: S3‑compatible object storage (Yandex Object Storage or another cloud S3 provider).
- **ASR Provider**: AssemblyAI via official Python SDK.
- **Hosting**: Dockerized services; target deployment on Yandex Cloud (containers + managed PostgreSQL + Object Storage).

## High‑Level Architecture
- A single FastAPI application (`backend/app/main.py`) exposes REST endpoints for:
  - authentication (`/auth/*`),
  - file management (presign/upload/download under `/files/*`),
  - transcription jobs (`/jobs/*`).
- The app uses:
  - `app/core/config.py` for settings (Pydantic `BaseSettings`, `.env` driven),
  - `app/db/*` for DB engine and session factory,
  - `app/models/*` for ORM models (users, transcription jobs, transcripts),
  - `app/schemas/*` for request/response DTOs,
  - `app/services/*` for domain logic (auth, storage, transcription),
  - `app/tasks/*` for async job runner and startup recovery.
- Background transcription is implemented with `asyncio.create_task` inside the FastAPI process (no external queue).

## Data Model (Conceptual)
- **User** – owns transcription jobs and authenticates via email/password + JWT.
- **Transcription Job** – references an uploaded media object, tracks status (`pending`, `processing`, `completed`, `failed`), language, and mode (mono/dialogue).
- **Transcript** – stores the resulting plain‑text transcript and, optionally, structured/diarized data.

Concrete columns and migrations live under `backend/alembic/versions/`; do not mirror full schemas here to avoid constant churn.

## Environments & Configuration
- Configuration is centralized in `app/core/config.py` and populated from environment variables:
  - `ENV` (`local` / `test` / `prod`),
  - `DATABASE_URL`,
  - `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`,
  - `ASSEMBLYAI_API_KEY`,
  - S3-related settings (`S3_ENDPOINT_URL`, credentials, bucket name, region),
  - resource limits like `MAX_PARALLEL_TRANSCRIPTIONS`.
- **Local/dev**:
  - `docker-compose.yml` brings up backend + frontend; provide real cloud S3 credentials because there is no local MinIO.
  - Database defaults to SQLite unless you point `DATABASE_URL` at your managed Postgres instance.
  - AssemblyAI is always required; use mocked fixtures in tests only.
- **Prod (Yandex Cloud)**:
  - FastAPI + Managed PostgreSQL + Object Storage (same S3 bucket pattern as local runs), with secrets injected via environment or secrets manager.
  - CI/CD should build and push images to a registry before deployment; Coolify or a similar orchestrator can consume `docker-compose.yml`.

### Quick comparison: prod vs. local
- **Database**: PostgreSQL in prod; SQLite by default in local, with the option to reuse PostgreSQL if configured.
- **Storage**: Single cloud S3 bucket in all environments (no MinIO or local filesystem fallback).
- **Transcription**: AssemblyAI everywhere; tests mock it to avoid external calls.
- **Orchestration**: Prod runs on Yandex Cloud (containers/VM + ingress/SSL); local uses `docker-compose` to run backend and frontend only.
- **Secrets**: Prod expects secrets from the platform (Lockbox/Secrets Manager or env vars); local relies on a checked-in `.env` file you copy from `.env.example`.

## Testing & Tooling
- Backend tests live in `backend/tests/` and use `pytest` + `pytest-asyncio` + `httpx.AsyncClient`.
- External services (AssemblyAI, S3) are abstracted via `app/services/*` and patched in tests to avoid network calls.
- Containers for backend and frontend are defined in `backend/Dockerfile` and `frontend/Dockerfile`; `docker-compose.yml` orchestrates them for local runs.
