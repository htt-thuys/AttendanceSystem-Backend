from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.ai_client import extract_face_data
from infrastructure.settings.runtime_settings import get_runtime_settings
from infrastructure.vector_db import qdrant_client
from modules.recognition import review_handler, scorer, sure_handler, unknown_handler


async def process_recognition(
    db: AsyncSession,
    image_bytes: bytes,
    camera_id: int | str | None,
    event_id: int | None = None,
    meeting_id: int | None = None,
    filename: str = "image.jpg",
    content_type: str = "image/jpeg",
) -> dict[str, Any]:
    face_data = await extract_face_data(
        image_bytes=image_bytes,
        filename=filename,
        content_type=content_type,
    )
    if face_data is None:
        return {"label": "no_face"}

    if face_data.get("spoof"):
        return {
            "label": "spoof_detected",
            "live_score": face_data.get("live_score"),
            "spoof_score": face_data.get("spoof_score"),
            "log_saved": False,
        }

    vector = face_data["vector"]
    face_quality = face_data["face_quality"]
    runtime_settings = await get_runtime_settings(db)

    results = qdrant_client.search_vectors(vector, top=5, only_active=True)
    scores = scorer.compute(results)
    top = scores[0] if scores else None

    if top and top["score"] >= runtime_settings.sure_threshold and top["gap"] >= runtime_settings.gap_min:
        return await sure_handler.handle(
            db,
            top,
            vector,
            face_quality,
            image_bytes,
            camera_id,
            event_id=event_id,
            meeting_id=meeting_id,
            cooldown_minutes=runtime_settings.recognition_log_cooldown_minutes,
        )

    if top and top["score"] >= runtime_settings.review_low:
        return await review_handler.handle(
            db,
            top,
            scores,
            vector,
            face_quality,
            image_bytes,
            camera_id,
            event_id=event_id,
            meeting_id=meeting_id,
            cooldown_minutes=runtime_settings.recognition_log_cooldown_minutes,
        )

    top_score = top["score"] if top else None
    return await unknown_handler.handle(
        db=db,
        vector=vector,
        image_bytes=image_bytes,
        camera_id=camera_id,
        event_id=event_id,
        meeting_id=meeting_id,
        face_quality=face_quality,
        top_score=top_score,
        dedup_threshold=runtime_settings.dedup_threshold,
    )
