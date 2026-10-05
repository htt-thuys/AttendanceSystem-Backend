# Project Structure

This document describes the backend structure that is currently running. It reflects the code as-is rather than a future target architecture.

## Runtime Overview

Current backend flow:
- `main.py` creates the FastAPI app, mounts static files, runs startup checks, and starts the periodic cleanup job.
- `api/router.py` includes routers directly from `modules/*/routes.py`.
- `modules/*` contains route, service, schema, and repository/query layers by domain.
- `infrastructure/*` contains runtime implementations for database sessions, ORM models, Qdrant, runtime settings, startup checks, cleanup, and email.
- `ai_server/*` contains face detection, embedding, and image-quality logic.
- `storage/*` contains runtime file-storage helpers.
- `db/migrations/*` contains Alembic migration files.

## Top-Level Layout

```text
.
|-- main.py
|-- api/
|   |-- router.py
|   `-- deps.py
|-- modules/
|   |-- auth/
|   |-- cameras/
|   |-- attendance/
|   |-- confirm/
|   |-- dashboard/
|   |-- events/
|   |-- export/
|   |-- recognition/
|   |-- recognition_logs/
|   |-- me/
|   |-- meetings/
|   |-- employees/
|   |-- users/
|   |-- unknown_queue/
|   |-- notifications/
|   |-- settings/
|   `-- cleanup/
|-- infrastructure/
|   |-- cleanup.py
|   |-- startup_checks.py
|   |-- ai_client.py
|   |-- email_sender.py
|   |-- database/
|   |-- settings/
|   `-- vector_db/
|-- ai_server/
|   |-- embedder.py
|   `-- utils.py
|-- storage/
|   |-- image_store.py
|   `-- cleanup.py
|-- db/
|   `-- migrations/
|-- scripts/
`-- docs/
```

## Active Route Layer

`main.py` includes `api.router` at the `/api` prefix.

`api/router.py` currently includes:
- `modules.auth.routes` at `/api/auth/*`
- `modules.cameras.routes` at `/api/cameras/*`
- `modules.attendance.routes` at `/api/attendance/*` and `/api/me/attendance`
- `modules.recognition.routes` at `/api/recognition`
- `modules.confirm.routes` at `/api/recognition/confirm`
- `modules.me.routes` at `/api/me/*`, including self-service meeting check-in/check-out/absence-request
- `modules.notifications.routes` at `/api/me/notifications/*`
- `modules.events.routes` at `/api/events/*`
- `modules.meetings.routes` at `/api/meetings/*`
- `modules.unknown_queue.routes` at `/api/unknown-queue/*`
- `modules.employees.routes` at `/api/employees/*`
- `modules.users.routes` at `/api/users/*` and `/api/employees/{emp_id}/account`
- `modules.recognition_logs.routes` at `/api/recognition-logs`
- `modules.settings.routes` at `/api/settings/*`
- `modules.cleanup.routes` at `/api/cleanup/run`
- `modules.dashboard.routes` at `/api/dashboard/*`
- `modules.export.routes` at `/api/export/*`

## Service And Repository Layer

Domain routes call their matching service modules directly:
- `modules.auth.routes` -> auth login service logic
- `modules.cameras.routes` -> `modules.cameras.service`
- `modules.attendance.routes` -> `modules.attendance.service`
- `modules.recognition.routes` -> `modules.recognition.service`
- `modules.confirm.routes` -> `modules.confirm.service`
- `modules.me.routes` -> `modules.me.service` and `modules.meetings.service`
- `modules.notifications.routes` -> `modules.notifications.service`
- `modules.events.routes` -> `modules.events.service`
- `modules.meetings.routes` -> `modules.meetings.service`
- `modules.employees.routes` -> `modules.employees.service`
- `modules.users.routes` -> `modules.users.service`
- `modules.unknown_queue.routes` -> `modules.unknown_queue.service`
- `modules.settings.routes` -> `modules.settings.service`
- `modules.cleanup.routes` -> `modules.cleanup.service`
- `modules.recognition_logs.routes` -> `modules.recognition_logs.service`
- `modules.dashboard.routes` -> `modules.dashboard.service`
- `modules.export.routes` -> `modules.export.service`

Active repository/query modules:
- `modules.employees.repository`
- `modules.users.repository`
- `modules.cameras.repository`
- `modules.events.repository`
- `modules.meetings.repository`
- `modules.unknown_queue.repository`
- `modules.recognition_logs.repository`
- `modules.settings.repository`
- `modules.attendance.repository`
- `modules.notifications.repository`
- `modules.dashboard.repository`

## Recognition Flow

Current recognition flow:

1. `modules.recognition.routes` receives the request.
2. `modules.recognition.service` handles business logic and auto-actions.
3. `modules.recognition.orchestrator` coordinates detection, scoring, and label selection.
4. `ai_server.embedder` detects faces, extracts embeddings, and computes quality.
5. `modules.recognition.sure_handler`, `review_handler`, or `unknown_handler` handles the result based on confidence.
6. `modules.recognition.runtime_store` stores temporary vectors in memory between `/api/recognition` and `/api/recognition/confirm`.
7. `modules.confirm.service` finalizes the recognition log and applies confirm side effects for employee vector upsert, meeting check-in, event attendance, or unknown queue.

## Infrastructure

Runtime infrastructure currently used:
- `infrastructure.database.session`
- `infrastructure.database.models`
- `infrastructure.vector_db.qdrant_client`
- `infrastructure.settings.runtime_settings`
- `infrastructure.startup_checks`
- `infrastructure.cleanup`
- `storage.image_store`
- `ai_server.embedder`

`main.py` imports:
- `run_startup_checks` from `infrastructure.startup_checks`
- `cleanup_old_images` and `run_periodic_cleanup` from `infrastructure.cleanup`
- `ensure_storage_dirs` from `storage.image_store`

## Where To Add New Code

- New domain route: `modules/<domain>/routes.py`
- New domain business logic: `modules/<domain>/service.py`
- New domain queries: `modules/<domain>/repository.py`
- Request/response schemas: `modules/<domain>/schemas.py`
- Internal domain helpers: `modules/<domain>/support.py`
- Recognition-specific runtime logic: `modules/recognition/*`
- ORM models: `infrastructure/database/models/`
- Database session, Qdrant, settings, startup, and cleanup logic: `infrastructure/*`
- AI/ML embedder logic: `ai_server/embedder.py` or `ai_server/utils.py`
- File storage: `storage/image_store.py`

## Related Documentation

- API contract: `docs/API_DOC.md`
- Database schema: `docs/DB_SCHEMA.md`
- Seed guide: `docs/SEED_DATA.md`
- Refactor progress: `docs/PROGRESS.md`
