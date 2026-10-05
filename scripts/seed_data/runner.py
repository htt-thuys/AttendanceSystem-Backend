from core.config import settings
from infrastructure.database.session import AsyncSessionLocal, engine
from infrastructure.vector_db.qdrant_client import ensure_collection_exists
from scripts.seed_data.constants import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    CAMERA_LOCATION,
    EMPLOYEE_PASSWORD,
    EMPLOYEES,
    UNKNOWN_QUEUE_SEED,
    build_seed_vector,
)
from scripts.seed_data.upserts import (
    seed_recognition_logs,
    upsert_camera,
    upsert_employee,
    upsert_face_vector,
    upsert_setting,
    upsert_unknown_queue,
    upsert_user,
)


def runtime_settings() -> dict[str, object]:
    return {
        "sure_threshold": settings.SURE_THRESHOLD,
        "review_low": settings.REVIEW_LOW,
        "gap_min": settings.GAP_MIN,
        "upsert_score_max": settings.UPSERT_SCORE_MAX,
        "upsert_min_vecs": settings.UPSERT_MIN_VECS,
        "dedup_threshold": settings.DEDUP_THRESHOLD,
        "image_retention_days": settings.IMAGE_RETENTION_DAYS,
    }


async def seed_users_and_employees(db):
    admin = await upsert_user(
        db=db,
        username=ADMIN_USERNAME,
        email=ADMIN_EMAIL,
        password=ADMIN_PASSWORD,
        role="admin",
    )

    employees = []
    for payload in EMPLOYEES:
        employee = await upsert_employee(db, payload, created_by=admin.id)
        await upsert_user(
            db=db,
            username=payload["username"],
            email=payload["email"],
            password=EMPLOYEE_PASSWORD,
            role="employee",
            employee_id=employee.id,
        )
        employees.append(employee)

    return admin, employees


async def seed_vectors(db, employees) -> None:
    for index, employee in enumerate(employees, start=1):
        await upsert_face_vector(
            db=db,
            employee_id=employee.id,
            qdrant_point_id=900000 + index,
            source_image_path=f"vector_sources/test/{employee.employee_code.lower()}_01.jpg",
            quality_score=240.0 + index,
            vector=build_seed_vector(index),
        )


async def seed() -> None:
    ensure_collection_exists()

    async with AsyncSessionLocal() as db:
        admin, employees = await seed_users_and_employees(db)
        camera = await upsert_camera(db, CAMERA_LOCATION)

        await seed_vectors(db, employees)
        await seed_recognition_logs(db, camera_id=camera.id, employee_ids=[e.id for e in employees])
        await upsert_unknown_queue(db, UNKNOWN_QUEUE_SEED)

        for key, value in runtime_settings().items():
            await upsert_setting(db, key, str(value), admin.id)

        await db.commit()

    await engine.dispose()

    print("Seed data inserted/updated.")
    print(f"Admin login: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    print(f"Employee login password: {EMPLOYEE_PASSWORD}")
