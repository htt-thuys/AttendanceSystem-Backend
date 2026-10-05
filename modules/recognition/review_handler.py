from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import RecognitionLog
from modules.recognition.runtime_store import temp_vectors
from storage.image_store import save_recognition_log_image


async def handle(
    db: AsyncSession,
    top_candidate: dict[str, Any],
    all_scores: list[dict[str, Any]],
    vector: list[float],
    face_quality: float,
    image_bytes: bytes,
    camera_id: int | str | None,
    event_id: int | None = None,
    meeting_id: int | None = None,
    cooldown_minutes: int = 0,
) -> dict[str, Any]:
    emp_id = top_candidate["employee_id"]
    top_score = top_candidate["score"]

    if isinstance(camera_id, str):
        camera_id = int(camera_id)

    image_path = await save_recognition_log_image(image_bytes)

    log_entry = RecognitionLog(
        camera_id=camera_id,
        event_id=event_id,
        meeting_id=meeting_id,
        face_image_path=image_path,
        result_label="review",
        top_score=top_score,
        employee_id=emp_id,
    )
    db.add(log_entry)
    await db.flush()

    temp_vectors[log_entry.id] = {
        "vector": vector,
        "face_quality": face_quality,
    }

    candidates = [
        {
            "employee_id": candidate["employee_id"],
            "score": candidate["score"],
        }
        for candidate in all_scores
    ]

    return {
        "label": "review",
        "employee_id": emp_id,
        "score": top_score,
        "candidates": candidates,
        "recognition_log_id": log_entry.id,
        "log_saved": True,
    }
