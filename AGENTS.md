# Repository Guidelines

## Project Structure & Module Organization
- `backend/` runs the FastAPI service: core app code under `app/`, data models in `app/models/`, API routers in `app/api/routers/`, and async tasks in `app/tasks/`. Alembic migrations live in `alembic/versions/`.
- `frontend/` contains the React + Vite client (`src/` for components, `public/` served by Vite, Docker assets for nginx deploys).
- Tests reside in `backend/tests/` and rely on fixtures that patch storage/transcription services for isolation.
- Shared documentation is kept in `README.md`, `backend/DOCS.md`, and `docs/*.md`; update them when workflows or architecture shift.

## Build, Test, and Development Commands
- Backend virtualenv: `python -m venv .venv && source .venv/bin/activate`, then `pip install -r requirements.txt`.
- Run API locally: `uvicorn app.main:app --reload --port 8000` (from `backend/` with `.env` in place).
- Apply migrations: `alembic upgrade head`.
- Frontend dev server: `npm install && npm run dev` (serve on port 5173 with proxy to backend).
- Docker compose stack: `docker compose up --build` brings up both services and mounts local storage.
- After any code or config change that should reflect in containers, run `docker compose up --build -d` to rebuild images and restart the stack.

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

---

## Agent Entry Point (White‑Coding)

When an agent starts working on a non‑trivial task in this repo, it should:

1. Read `README.md` to understand the project at a high level and check the **Current Plan Step** section to see what is in progress right now.
2. Read `docs/product.md` and `docs/tech.md` to get the product and technical context.
3. For backend‑heavy tasks, also scan `backend/DOCS.md` and relevant modules under `backend/app/`.
4. For frontend‑heavy tasks, inspect `frontend/` (`src/App.jsx`, `src/main.jsx`, `styles.css`) and any docs that may be added later.

If web access is available and the task involves design decisions or unfamiliar tools, first search for current best practices (framework usage, security, deployment) and apply them to this codebase.

## Planning System (`plans/`)

For any task that is more than a one‑off script or tiny fix, use a written plan to keep context between sessions and chats.

- Plans live in the `plans/` directory.
- File naming: `NNN-short-name.md`, where:
  - `NNN` is a three‑digit sequence (`001`, `002`, …),
  - `short-name` briefly reflects the objective (e.g. `001-mvp-backend`, `002-add-billing`).
- Inside each plan, use this structure:
  - `## Objective` – a concise restatement of the macro‑task in business terms.
  - `## Steps` – step‑by‑step breakdown into small, checkable sub‑tasks that reference relevant code and docs.
  - `## Risks` – potential problems (technical, product, infra) and how to mitigate them.
  - `## Rollback` – how to undo or safely disable the change if it goes wrong (often via `git` or feature flags).

Workflow:
- Create or update a plan before starting substantial work (new features, refactors, migrations, infra changes).
- Implement work stage by stage, keeping the plan in sync when scope changes.
- Keep plans reasonably short and focused on one macro‑task; create a new plan rather than turning one file into a logbook.

When plans are usually **not** needed:
- Very small, throwaway utilities.
- One‑off calculations or experiments that will not be committed.
- Tiny, localized fixes that clearly fit into a single context window and do not change product behavior in a major way.

## Plan Progress in `README.md`

The **Current Plan Step** section in `README.md` is the canonical pointer to the active plan and step:

- It must always reflect the single active plan (by filename in `plans/`) and the step that is currently being executed.
- When you finish a step and move to the next one, update this section to describe the new step.
- When a plan is completed or paused, set the active plan and step to `_none_` or adjust them to the next relevant plan.
- If scope changes and the plan file is updated, also synchronize the description in `README.md` so it stays accurate.

## Documentation Expectations for Agents

When an agent modifies behavior, architecture, or workflows, it should:

- Update `README.md` when CLI commands, environment setup, or high‑level usage flow change.
- Update `backend/DOCS.md` for meaningful backend architecture or flow changes (new services, queues, external providers).
- Update `docs/product.md` if product goals, user flows, or target users shift.
- Update `docs/tech.md` if the stack, key components, or deployment approach change.

Keep documentation:
- High‑level and stable in `docs/*.md` so it remains a good prompt for future agents.
- Free of volatile details like full table schemas or every field of every API; point to code and migrations instead.
