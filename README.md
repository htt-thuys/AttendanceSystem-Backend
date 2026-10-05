# Face Recognition Attendance System Backend

Backend for the facial recognition attendance system, built on **FastAPI + PostgreSQL + Qdrant**. The service provides authentication, employee and attendance management, recognition orchestration, event/meeting check-in, reporting, exports, and runtime cleanup for stored images and vector data.

## 1. Project Objectives

This repository handles the entire server-side application for the attendance system. Key responsibilities include:

- **API Service Layer:** Expose REST APIs for authentication, recognition, attendance, employees, users, meetings, events, dashboard data, settings, and exports.
- **Recognition Orchestration:** Receive camera frames, call the external AI embedding server, compare face vectors in Qdrant, classify results, and trigger attendance side effects.
- **Data Persistence:** Store business data in PostgreSQL through SQLAlchemy models and Alembic migrations.
- **Vector Storage:** Store and query employee face embeddings in Qdrant.
- **Runtime Operations:** Serve stored images, run startup checks, clean old runtime files, and support seed/bootstrap scripts for local development.
- **Authorization Management:** Enforce role-based access control using JWT bearer tokens.

## 2. Technologies Used

| Category             | Core Technologies                                      |
| :------------------- | :----------------------------------------------------- |
| **Core**             | Python 3.11, FastAPI, Uvicorn                          |
| **Database**         | PostgreSQL, SQLAlchemy Async ORM, Alembic, asyncpg     |
| **Vector Database**  | Qdrant, qdrant-client                                  |
| **AI / Recognition** | External AI server, OpenCV headless, NumPy             |
| **Auth / Security**  | JWT (`python-jose`), bcrypt, HTTP Bearer authentication |
| **Configuration**    | pydantic-settings, python-dotenv                       |
| **Deployment**       | Docker, Docker Compose                                 |
| **HTTP / Files**     | httpx, python-multipart, FastAPI StaticFiles           |

## 3. Key Features

### Recognition & Attendance

- Receive face images through `POST /api/recognition`.
- Support recognition labels: **sure**, **review**, **unknown**, and **no_face**.
- Match detected face embeddings against Qdrant vectors.
- Apply recognition cooldown to avoid duplicate logs and repeated auto-actions.
- Save recognition logs and runtime face images.
- Confirm ambiguous results through `POST /api/recognition/confirm`.
- Automatically upsert useful face vectors after confirmed matches.

### Attendance, Meetings, and Events

- Daily attendance listing, today summary, report generation, status updates, and CSV export.
- Personal attendance history and absence requests through `/api/me/*`.
- Meeting creation, participant management, check-in/check-out, absence request, completion, and attendance summary.
- Event scheduling and event attendance derived from confirmed recognition logs.
- Public meeting/event listing for kiosk or tablet recognition screens.

### Administrative Area

Comprehensive APIs for operational modules:

- `Employees` and face vectors
- `Users / Accounts`
- `Unknown queue`
- `Cameras`
- `Recognition logs`
- `Dashboard`
- `Settings`
- `Cleanup`
- `Export`

### Runtime Infrastructure

- Startup checks for database and vector database readiness.
- Static serving of runtime images under `/media`.
- Periodic cleanup of old images, resolved queue entries, stale notifications, and orphaned storage/vector records.
- Docker Compose services for API, PostgreSQL, Qdrant, and optional seed execution.

## 4. System Authorization (RBAC)

The backend uses JWT bearer authentication and organizes protected APIs around 3 main roles: **Employee**, **Reviewer**, and **Admin**.

> **Authorization Principles:**
>
> - Public endpoints include health check, login/refresh, recognition, recognition confirmation, recent public logs, active employees, and public meeting/event lists.
> - `employee` can access personal self-service endpoints under `/api/me/*`, including profile, password, notifications, attendance, and meeting actions.
> - `reviewer` can access review-focused modules such as employees read views, recognition logs, unknown queue, meetings read views, and events read views.
> - `admin` has full access to management, configuration, export, cleanup, and dashboard endpoints.

_For the complete endpoint-level contract, see: [docs/API_DOC.md](docs/API_DOC.md)._

## 5. Directory Structure

The project applies a modular backend architecture for easy scalability and maintenance:

```text
.
|-- main.py                         # FastAPI app, CORS, static files, startup/cleanup lifecycle
|-- api/
|   |-- router.py                   # Includes all domain routers under /api
|   `-- deps.py                     # Auth and RBAC dependencies
|-- core/
|   |-- config.py                   # Runtime settings from .env
|   `-- security.py                 # JWT and password helpers
|-- modules/
|   |-- auth/                       # Login and refresh token APIs
|   |-- attendance/                 # Daily attendance, reports, exports, self-service absence
|   |-- cameras/                    # Camera device management
|   |-- cleanup/                    # Manual cleanup API
|   |-- confirm/                    # Recognition confirmation side effects
|   |-- dashboard/                  # Dashboard statistics APIs
|   |-- employees/                  # Employee CRUD, avatars, vectors, personal logs
|   |-- events/                     # Event schedule and attendance APIs
|   |-- export/                     # CSV export APIs
|   |-- me/                         # Current user profile and self-service APIs
|   |-- meetings/                   # Meeting management and participant services
|   |-- notifications/              # Current user notification APIs
|   |-- recognition/                # Recognition flow, scoring, handlers, runtime store
|   |-- recognition_logs/           # Recognition log queries
|   |-- settings/                   # Runtime threshold and cleanup settings
|   |-- unknown_queue/              # Unrecognized face review queue
|   `-- users/                      # Employee account management
|-- infrastructure/
|   |-- database/                   # SQLAlchemy sessions and ORM models
|   |-- settings/                   # Persisted runtime settings
|   |-- vector_db/                  # Qdrant client
|   |-- ai_client.py                # External AI server client
|   |-- cleanup.py                  # Periodic cleanup job
|   |-- email_sender.py             # SMTP integration
|   `-- startup_checks.py           # Startup readiness checks
|-- ai_server/
|   |-- embedder.py                 # Face detection / embedding adapter logic
|   `-- utils.py                    # AI image utility logic
|-- storage/
|   |-- image_store.py              # Runtime image storage helpers
|   `-- cleanup.py                  # Storage cleanup helpers
|-- db/
|   `-- migrations/                 # Alembic migration environment and versions
|-- scripts/                        # Seed, bootstrap, API test, and perf scripts
`-- docs/                           # API, DB, structure, seed, and frontend guide docs
```

_For more structural details, see: [docs/STRUCTURE.md](docs/STRUCTURE.md)._

## 6. Facial Recognition Flow

The `/api/recognition` endpoint is the heart of the backend recognition workflow. The processing flow occurs in the following steps:

1. **Request:** `modules.recognition.routes` receives a multipart image and optional context such as `camera_id`, `meeting_id`, or `event_id`.
2. **Service:** `modules.recognition.service` validates business context and coordinates auto-actions.
3. **Orchestration:** `modules.recognition.orchestrator` calls the embedding logic, computes scores, and selects the recognition label.
4. **AI Processing:** `ai_server.embedder` detects faces, extracts embeddings, and computes image quality using the external AI service.
5. **Vector Matching:** Qdrant is queried for candidate employee vectors.
6. **Handling:** `sure_handler`, `review_handler`, or `unknown_handler` applies the correct path based on confidence and score gap.
7. **Temporary State:** `runtime_store` keeps temporary vectors between `/api/recognition` and `/api/recognition/confirm`.
8. **Confirmation:** `modules.confirm.service` finalizes logs and applies side effects such as vector upsert, daily attendance, meeting check-in, event attendance, or unknown queue updates.

_Core files to note: `modules/recognition/service.py`, `modules/recognition/orchestrator.py`, `modules/confirm/service.py`, `ai_server/embedder.py`, and `infrastructure/vector_db/qdrant_client.py`._

## 7. Local Setup & Run

### Environment Requirements

- **Python 3.11+**
- **PostgreSQL**
- **Qdrant**
- **External AI embedding server**
- **Docker and Docker Compose** for the recommended setup

### Recommended Docker Setup

```powershell
# 1. Copy environment variables
Copy-Item .env.example .env

# 2. Update .env with AI server and security settings
# AI_SERVER_HOST=172.16.75.66
# AI_SERVER_EMBED_PORT=8002
# SECRET_KEY=change-this-to-a-secure-random-string

# 3. Build and start services
docker compose up -d --build
```

Docker Compose starts:

- `api`: FastAPI backend at `http://127.0.0.1:8000`
- `postgres`: PostgreSQL database `face_recognition`
- `qdrant`: vector database at `http://127.0.0.1:6333`

The API container automatically runs migrations on startup through `docker-entrypoint.sh`:

```powershell
python -m alembic upgrade head
```

### Local Python Setup

Run locally only when debugging Python directly on the host machine.

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 2. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Copy configuration and update values
Copy-Item .env.example .env

# 4. Run migrations
python -m alembic upgrade head

# 5. Start the development server
$env:PYTHONIOENCODING='utf-8'
uvicorn main:app --reload
```

> The API runs by default at: `http://127.0.0.1:8000`

### Environment Variables

Copy `.env.example` to `.env` and configure it before running. The most important variables are:

- `DATABASE_URL`: PostgreSQL async connection string.
- `QDRANT_URL`: Qdrant service URL.
- `QDRANT_COLLECTION`: Collection used for face embeddings.
- `SECRET_KEY`: JWT signing key.
- `BACKEND_CORS_ORIGINS`: Comma-separated allowed frontend origins.
- `BACKEND_CORS_ORIGIN_REGEX`: Optional regex for dynamic origins such as ngrok.
- `AI_SERVER_HOST`, `AI_SERVER_EMBED_PORT`, `AI_SERVER_PREFIX`, `AI_SERVER_TIMEOUT`: External AI server connection settings.
- `IMAGE_STORAGE_PATH`, `IMAGE_PUBLIC_BASE`: Runtime image storage and public media path.
- `SURE_THRESHOLD`, `REVIEW_LOW`, `GAP_MIN`, `UPSERT_SCORE_MAX`, `UPSERT_MIN_VECS`, `DEDUP_THRESHOLD`: Recognition decision thresholds.
- `RECOGNITION_LOG_COOLDOWN_MINUTES`, `IMAGE_RETENTION_DAYS`, `IMAGE_CLEANUP_INTERVAL_HOURS`: Runtime behavior and cleanup settings.

### Other Commands

| Command                                      | Function                                      |
| :------------------------------------------- | :-------------------------------------------- |
| `docker compose up -d --build`               | Build and run API, PostgreSQL, and Qdrant.    |
| `docker compose logs -f api`                 | Follow backend API logs.                      |
| `docker compose down`                        | Stop Docker services.                         |
| `docker compose --profile seed run --rm seed` | Seed sample data through Docker Compose.      |
| `python -m alembic upgrade head`             | Run database migrations locally.              |
| `python scripts/bootstrap_admin.py ...`      | Create an initial admin user manually.        |
| `python scripts/seed_test_data.py`           | Seed sample data locally.                     |
| `python scripts/test_recognition_api.py --image path/to/face.jpg` | Test recognition API with a local image. |

## 8. Docker Deployment

The project includes built-in Docker configuration via `docker-compose.yml`, `Dockerfile`, and `docker-entrypoint.sh`.

```powershell
# Build the image and run the services in the background
docker compose up -d --build
```

- **API Port:** `8000`
- **PostgreSQL Port:** `5432`
- **Qdrant Ports:** `6333` and `6334`
- **Runtime Image Volume:** `app_images`, mounted at `/app/storage/images`
- **Qdrant Volume:** `qdrant_data`
- **PostgreSQL Volume:** `postgres_data`

Seed data is intentionally not run with the server by default. To create sample data:

```powershell
docker compose --profile seed run --rm seed
```

Default seed login:

```text
username: admin
password: admin123
```

## 9. Development Conventions & Document Reading Order

To maintain clean and consistent backend code, please adhere to the following:

- Place domain routes in `modules/<domain>/routes.py`.
- Place business logic in `modules/<domain>/service.py` or a domain-specific service submodule.
- Place database query helpers in `modules/<domain>/repository.py`.
- Place request/response schemas in `modules/<domain>/schemas.py`.
- Place ORM models under `infrastructure/database/models/`.
- Keep infrastructure integrations under `infrastructure/*`.
- Keep recognition-specific runtime logic inside `modules/recognition/*`.
- Do not commit `.env`, `.venv/`, `storage/images/`, `__pycache__/`, or generated runtime files.
- Commit new Alembic migration files whenever database schema changes.

**Reading order for newcomers:**

1. `README.md` -> 2. `docs/STRUCTURE.md` -> 3. `docs/API_DOC.md` -> 4. `docs/DB_SCHEMA.md` -> 5. `docs/SEED_DATA.md` -> 6. `main.py` -> 7. `api/router.py` -> 8. `modules/recognition/service.py`

## 10. Project Status & Frontend Integration

### Project Status

Current known incomplete items:

- Meeting attendance is not yet updated after an unknown-queue item is processed and resolved.
- User notifications for meeting invitations are not finished yet. The notification module exists, but the meeting invitation notification flow still needs completion.
- Camera management is not fully completed yet.

### Frontend Integration

For frontend API integration, read [docs/API_DOC.md](docs/API_DOC.md) and implement according to the documented endpoints, request payloads, response shapes, and RBAC requirements.

> Important notes when developing new features:
>
> - Always update [docs/API_DOC.md](docs/API_DOC.md) when endpoint behavior or response schemas change.
> - Update [docs/DB_SCHEMA.md](docs/DB_SCHEMA.md) and add Alembic migrations when database models change.
> - Keep [docs/STRUCTURE.md](docs/STRUCTURE.md) synchronized when modules or major runtime flow change.

---

If you are continuing development on this repository, start by reading the module directly related to the feature you are about to modify, then verify the API contract and database schema before writing code. This helps keep the backend architecture consistent and prevents diverging behavior between server modules and frontend screens.
