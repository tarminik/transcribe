# transcribe

## Current Plan Step

This section tracks the currently active plan and step for white‑coding.

- Active plan: _none_ (set to a file in `plans/` once you create one).
- Current step: _none_ (update with a short description of the step being executed).

Always keep this section in sync when you switch plans or move to the next step so that humans and agents can quickly see what to do next.

## Backend Quick Start (local only)

1. `cd backend` and create a virtualenv (`python -m venv .venv` then `source .venv/bin/activate`).
2. Install deps: `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and adjust secrets as needed. Defaults use SQLite, local filesystem storage, and the stub transcriber.
4. Run migrations: `alembic upgrade head` (creates `dev.db`).
5. Start the API: `uvicorn app.main:app --reload`.

`/files/presign` returns local upload/download URLs when `STORAGE_BACKEND=local`; authenticate and `PUT` the upload URL with `multipart/form-data` to store files. Jobs created while `TRANSCRIPTION_BACKEND=stub` will complete immediately using the uploaded `.txt` contents.

## Frontend Quick Start

1. `cd frontend` and copy `.env.example` to `.env` (defaults assume backend on `http://localhost:8000`).
2. Install deps: `npm install`.
3. Run the dev server: `npm run dev` (launches Vite on port 5173 with proxying to the backend).

The UI offers a minimal flow: sign up or sign in with email/password, upload a file, pick language and mono/dialogue mode, and trigger transcription. When the backend finishes, the transcript preview appears and can be downloaded as `.txt`.

## Container Images

- Backend: `backend/Dockerfile` builds a slim Python 3.12 image that installs `requirements.txt` and runs `uvicorn app.main:app` on port 8000. A `.dockerignore` is provided to keep build contexts small.
- Frontend: `frontend/Dockerfile` builds the Vite app and serves it from `nginx:alpine` (port 80). Configure `VITE_API_BASE` and `VITE_BACKEND_ORIGIN` via build args if you need to point at a different API.
- Compose: `docker-compose.yml` launches both services locally (`backend` on 8000, `frontend` on 5173) and persists stub transcripts under the `backend-storage` volume.

## Deployment Notes

- Coolify: Deploy either service using the Dockerfile build pack or deploy both via the included `docker-compose.yml`. Point the base directory to `/` and set the compose path to `/docker-compose.yml`. Configure secrets (database URL, JWT secret, AssemblyAI key, S3/Yandex credentials) in the Coolify environment UI.
- Yandex Cloud: Recommended architecture uses Managed Service for PostgreSQL, Object Storage (S3-compatible), and Container Registry. Provision a Compute Cloud VM (or Container Optimized Image) running Coolify or Docker and attach the necessary security groups. When using Managed PostgreSQL, download the CA cert and set `sslmode=verify-full` in `DATABASE_URL`.
- CI/CD: Use GitHub Actions to build and push both images to a registry (e.g., GitHub Container Registry). Coolify can deploy automatically by tracking the default branch or listening to Git webhooks.
