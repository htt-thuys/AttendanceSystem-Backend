# Test Data Seed

This document explains how to create sample data for local and development environments.

## When To Run The Seed

Run the seed after the backend, PostgreSQL, and Qdrant have started through Docker Compose.

The seed does not run with the server by default to avoid creating test data unintentionally.

## Run Seed With Docker

From the project root:

```powershell
docker compose --profile seed run --rm seed
```

The `seed` service uses the same backend image and goes through `docker-entrypoint.sh`, so migrations run before the seed starts.

## Accounts Created By Seed

Admin:

```text
username: admin
password: admin123
```

Sample employees:

```text
username: an
username: binh
username: chau
password: employee123
```

## Data Created

The seed script currently creates or updates:
- admin user
- employee users
- sample employees
- sample camera
- sample recognition logs
- sample unknown queue items
- runtime settings from `.env`
- vector metadata in PostgreSQL
- 512-d vector points in Qdrant

## Idempotency

The seed can run multiple times. It finds existing data by stable keys such as username, employee code, camera location, image path, or Qdrant point ID, then updates records instead of creating duplicates.

## Seed Code Structure

Entrypoint:
- `scripts/seed_test_data.py`

Main logic:
- `scripts/seed_data/constants.py`: sample data and deterministic seed vectors
- `scripts/seed_data/upserts.py`: idempotent PostgreSQL/Qdrant upsert helpers
- `scripts/seed_data/runner.py`: seed execution order

Docker Compose calls this entrypoint:

```yaml
command: python scripts/seed_test_data.py
```

## Run Seed Without Docker

Use this only when debugging the backend directly on the host machine.

Requirements:
- dependencies installed in `.venv`
- PostgreSQL and Qdrant running
- `.env` points to the correct `DATABASE_URL` and `QDRANT_URL`
- migrations have already run

Command:

```powershell
.\.venv\Scripts\python.exe scripts\seed_test_data.py
```
