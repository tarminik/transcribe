## Objective
Add a simple transcription history view so users can browse past transcriptions and read their text, backed by a dedicated database table and exposed through the API and UI.

## Steps
1. **Data model & migration** — Design a transcription history table linked to transcription jobs/users, add the SQLAlchemy model, Alembic migration, and any schema updates needed to surface history entries.
2. **API & service layer** — Populate history entries when a job completes, and expose endpoints for listing history and fetching the transcript text for a specific entry with proper auth checks.
3. **Frontend experience** — Add a history section in the UI that lists past transcriptions for the signed-in user and lets them open a transcript’s text.

## Risks
- Large transcript payloads could make list responses heavy; mitigate by keeping the list lightweight and fetching full text per entry.
- Inconsistent data if history creation fails during job completion; ensure operations occur within the existing processing flow and handle missing transcripts gracefully.

## Rollback
- Drop or ignore the new API routes and history table via migration rollback; remove UI calls to the history endpoints to revert to the current upload-only experience.
