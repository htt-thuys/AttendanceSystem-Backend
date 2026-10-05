from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.ai_client import AIClientError
from infrastructure.database.session import get_db
from modules.recognition import service
from modules.recognition.schemas import RecognizeResponse

recognize_router = APIRouter()


@recognize_router.post("/recognition", response_model=RecognizeResponse)
async def recognize_face(
    image: UploadFile = File(...),
    camera_id: str | None = Form(None),
    meeting_id: str | None = Form(None),
    event_id: str | None = Form(None),
    event_id_camel: str | None = Form(None, alias="eventId"),
    event_id_query: str | None = Query(None, alias="event_id"),
    event_id_query_camel: str | None = Query(None, alias="eventId"),
    db: AsyncSession = Depends(get_db),
):
    try:
        image_bytes = await image.read()

        try:
            normalized_camera_id = int(camera_id) if camera_id and camera_id.strip() else None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="camera_id khong hop le") from exc

        try:
            normalized_meeting_id = int(meeting_id) if meeting_id and meeting_id.strip() else None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="meeting_id khong hop le") from exc

        raw_event_id = _first_non_empty(event_id, event_id_camel, event_id_query, event_id_query_camel)
        try:
            normalized_event_id = int(raw_event_id) if raw_event_id else None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="event_id khong hop le") from exc

        return await service.recognize_face(
            db=db,
            image_bytes=image_bytes,
            camera_id=normalized_camera_id,
            meeting_id=normalized_meeting_id,
            event_id=normalized_event_id,
            filename=image.filename or "image.jpg",
            content_type=image.content_type or "image/jpeg",
        )
    except AIClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except HTTPException:
        raise


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None
