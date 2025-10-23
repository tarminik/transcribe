# transcribe

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

The UI offers a minimal flow: sign in with your API credentials, upload a file, pick language and mono/dialogue mode, and trigger transcription. When the backend finishes, the transcript preview appears and can be downloaded as `.txt`.
