# Repository Guidelines

## Project Structure & Module Organization
- `backend/` runs the FastAPI service: core app code under `app/`, data models in `app/models/`, API routers in `app/api/routers/`, and async tasks in `app/tasks/`. Alembic migrations live in `alembic/versions/`.
- `frontend/` contains the React + Vite client (`src/` for components, `public/` served by Vite, Docker assets for nginx deploys).
- Tests reside in `backend/tests/` and rely on fixtures that patch storage/transcription services for isolation.
- Shared documentation is kept in `README.md` and `DOCS.md`; update both when workflows or architecture shift.

## Build, Test, and Development Commands
- Backend virtualenv: `python -m venv .venv && source .venv/bin/activate`, then `pip install -r requirements.txt`.
- Run API locally: `uvicorn app.main:app --reload --port 8000` (from `backend/` with `.env` in place).
- Apply migrations: `alembic upgrade head`.
- Frontend dev server: `npm install && npm run dev` (serve on port 5173 with proxy to backend).
- Docker compose stack: `docker compose up --build` brings up both services and mounts local storage.

## Coding Style & Naming Conventions
- Follow PEP 8 for Python; keep imports sorted (use `isort` manually if needed) and format with 4-space indentation.
- Prefer async/await patterns already established; reuse `get_session_factory()` and dependency overrides.
- React components stay in PascalCase (`App.jsx`), hooks in camelCase, and CSS classes in BEM-like lowercase-with-hyphen.
- Config keys mirror existing `.env.example` files; add new settings with uppercase snake_case aliases in `Settings`.

## Testing Guidelines
- Python tests use `pytest` with `pytest-asyncio`; run `pytest` from `backend/` after installing dev deps.
- Name async tests with `test_*` and decorate with `@pytest.mark.asyncio` when needed.
- Ensure new API routes have integration coverage in `backend/tests/test_api.py` or a sibling module.
- When adding storage/transcription logic, extend fixtures in `tests/conftest.py` to avoid hitting external services.

## Commit & Pull Request Guidelines
- Commit messages should be imperative and scoped (e.g., `feat(auth): add password reset endpoint`); align with existing Conventional Commit style.
- Before opening a PR, run backend tests and relevant frontend builds; note results in the description.
- PRs must include: summary of changes, testing evidence, linked issue/ticket, and screenshots or GIFs for UI-impacting work.
- Flag environment or migration impacts explicitly, and provide rollback notes when altering schemas or deployment files.
