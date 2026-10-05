from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from core.security import hash_password
from infrastructure.database.models import (
    Camera,
    Employee,
    FaceVector,
    RecognitionLog,
    SystemSetting,
    UnknownQueue,
    User,
)
from infrastructure.vector_db.qdrant_client import upsert_vector


async def upsert_user(
    db,
    username: str,
    email: str,
    password: str,
    role: str,
    employee_id: int | None = None,
) -> User:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None and email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    values = {
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "role": role,
        "is_active": True,
        "employee_id": employee_id,
    }

    if user is None:
        user = User(**values)
        db.add(user)
        await db.flush()
        return user

    for field, value in values.items():
        setattr(user, field, value)
    return user


async def upsert_employee(db, payload: dict, created_by: int) -> Employee:
    result = await db.execute(
        select(Employee).where(Employee.employee_code == payload["employee_code"])
    )
    employee = result.scalar_one_or_none()

    values = {
        "full_name": payload["full_name"],
        "employee_code": payload["employee_code"],
        "avatar_path": payload["avatar_path"],
        "status": "active",
        "metadata_": {"seed": True, "department": "Test"},
        "created_by": created_by,
    }

    if employee is None:
        employee = Employee(**values)
        db.add(employee)
        await db.flush()
        return employee

    for field, value in values.items():
        setattr(employee, field, value)
    return employee


async def upsert_camera(db, location: str) -> Camera:
    result = await db.execute(select(Camera).where(Camera.location == location))
    camera = result.scalar_one_or_none()

    if camera is None:
        camera = Camera(location=location, is_active=True)
        db.add(camera)
        await db.flush()
        return camera

    camera.is_active = True
    return camera


async def upsert_face_vector(
    db,
    employee_id: int,
    qdrant_point_id: int,
    source_image_path: str,
    quality_score: float,
    vector: list[float],
) -> FaceVector:
    result = await db.execute(
        select(FaceVector).where(FaceVector.qdrant_point_id == qdrant_point_id)
    )
    face_vector = result.scalar_one_or_none()

    values = {
        "employee_id": employee_id,
        "qdrant_point_id": qdrant_point_id,
        "source": "seed",
        "source_image_path": source_image_path,
        "quality_score": quality_score,
        "score_at_create": None,
        "is_active": True,
    }

    if face_vector is None:
        face_vector = FaceVector(**values)
        db.add(face_vector)
        await db.flush()
    else:
        for field, value in values.items():
            setattr(face_vector, field, value)

    upsert_vector(
        qdrant_point_id,
        vector,
        {
            "employee_id": employee_id,
            "face_vec_id": face_vector.id,
            "is_active": True,
            "source": "seed",
        },
    )
    return face_vector


async def seed_recognition_logs(db, camera_id: int, employee_ids: list[int]) -> None:
    result = await db.execute(
        select(RecognitionLog).where(
            RecognitionLog.face_image_path.like("recognition_logs/test/%")
        )
    )
    if result.scalars().first():
        return

    now = datetime.now(timezone.utc)
    db.add_all(
        [
            RecognitionLog(
                camera_id=camera_id,
                captured_at=now - timedelta(minutes=20),
                face_image_path="recognition_logs/test/sure_emp001.jpg",
                result_label="sure",
                top_score=0.82,
                employee_id=employee_ids[0],
                final_label="sure",
            ),
            RecognitionLog(
                camera_id=camera_id,
                captured_at=now - timedelta(minutes=12),
                face_image_path="recognition_logs/test/review_emp002.jpg",
                result_label="review",
                top_score=0.33,
                employee_id=employee_ids[1],
                final_label="review",
            ),
            RecognitionLog(
                camera_id=camera_id,
                captured_at=now - timedelta(minutes=5),
                face_image_path="recognition_logs/test/unknown_001.jpg",
                result_label="unknown",
                top_score=0.18,
                final_label="unknown",
            ),
        ]
    )


async def upsert_unknown_queue(db, payload: dict) -> UnknownQueue:
    result = await db.execute(
        select(UnknownQueue).where(UnknownQueue.image_path == payload["image_path"])
    )
    queue_item = result.scalar_one_or_none()

    values = {
        "image_path": payload["image_path"],
        "vector": payload["vector"],
        "face_quality": payload["face_quality"],
        "attempt_count": payload["attempt_count"],
        "resolved_at": None,
        "resolved_by": None,
    }

    if queue_item is None:
        queue_item = UnknownQueue(**values)
        db.add(queue_item)
        await db.flush()
        return queue_item

    for field, value in values.items():
        setattr(queue_item, field, value)
    return queue_item


async def upsert_setting(db, key: str, value: str, updated_by: int) -> SystemSetting:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()

    if setting is None:
        setting = SystemSetting(key=key, value=value, updated_by=updated_by)
        db.add(setting)
        await db.flush()
        return setting

    setting.value = value
    setting.updated_by = updated_by
    return setting
