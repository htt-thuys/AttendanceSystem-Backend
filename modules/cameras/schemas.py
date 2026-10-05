from datetime import datetime

from pydantic import BaseModel, Field


class CameraResponse(BaseModel):
    """Camera configuration shown in admin screens."""

    id: int
    location: str | None = None
    is_active: bool


class CameraCreateRequest(BaseModel):
    """Payload to create a camera record."""

    location: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class CameraUpdateRequest(BaseModel):
    """Payload to update camera metadata."""

    location: str | None = Field(default=None, max_length=500)


class CameraStatusUpdateRequest(BaseModel):
    """Payload to activate or deactivate a camera."""

    is_active: bool


class CameraDetailResponse(CameraResponse):
    """Camera response with the latest recognition timestamp."""

    last_seen_at: datetime | None = None
