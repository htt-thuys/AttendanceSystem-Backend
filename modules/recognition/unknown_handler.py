from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import RecognitionLog, UnknownQueue
from storage.image_store import copy_to_unknown_queue, save_recognition_log_image


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two face vectors."""
    a = np.array(v1)
    b = np.array(v2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


async def handle(
    db: AsyncSession,
    vector: list[float],
    image_bytes: bytes,
    camera_id: int | str | None,
    event_id: int | None,
    meeting_id: int | None,
    face_quality: float | None,
    top_score: float | None,
    dedup_threshold: float,
) -> dict[str, Any]:
    """Handle unknown faces and create a log only for a new queue item."""
    effective_face_quality = face_quality if face_quality is not None else 0.0

    if isinstance(camera_id, str):
        camera_id = int(camera_id)

    result = await db.execute(
        select(UnknownQueue).where(
            UnknownQueue.resolved_at.is_(None),
            UnknownQueue.event_id == event_id,
            UnknownQueue.meeting_id == meeting_id,
        )
    )
    unresolved_list = result.scalars().all()

    best_match = None
    best_sim = -1.0

    for unknown_item in unresolved_list:
        sim = cosine_similarity(vector, unknown_item.vector)
        if sim > best_sim:
            best_sim = sim
            best_match = unknown_item

    if best_match and best_sim > dedup_threshold:
        best_match.attempt_count += 1
        best_match.last_seen_at = func.now()

        if effective_face_quality > (best_match.face_quality or 0):
            image_path = await save_recognition_log_image(image_bytes)
            best_match.face_quality = effective_face_quality
            best_match.image_path = await copy_to_unknown_queue(image_path)
            best_match.vector = vector

        await db.flush()
        return {
            "label": "unknown",
            "recognition_log_id": None,
            "log_saved": False,
        }

    recognition_log_path = await save_recognition_log_image(image_bytes)
    db.add(
        UnknownQueue(
            camera_id=camera_id,
            event_id=event_id,
            meeting_id=meeting_id,
            image_path=await copy_to_unknown_queue(recognition_log_path),
            vector=vector,
            face_quality=effective_face_quality,
            attempt_count=1,
        )
    )

    log_entry = RecognitionLog(
        camera_id=camera_id,
        event_id=event_id,
        meeting_id=meeting_id,
        face_image_path=recognition_log_path,
        result_label="unknown",
        top_score=top_score,
    )
    db.add(log_entry)
    await db.flush()

    return {
        "label": "unknown",
        "recognition_log_id": log_entry.id,
        "log_saved": True,
    }
