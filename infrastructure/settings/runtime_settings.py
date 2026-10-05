from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from modules.settings import repository


@dataclass
class RuntimeSettings:
    sure_threshold: float
    review_low: float
    gap_min: float
    upsert_score_max: float
    upsert_min_vecs: int
    dedup_threshold: float
    image_retention_days: int
    recognition_log_cooldown_minutes: int
    event_tablet_lookahead_minutes: int


SETTING_DEFINITIONS: dict[str, tuple[str, type]] = {
    "sure_threshold": ("SURE_THRESHOLD", float),
    "review_low": ("REVIEW_LOW", float),
    "gap_min": ("GAP_MIN", float),
    "upsert_score_max": ("UPSERT_SCORE_MAX", float),
    "upsert_min_vecs": ("UPSERT_MIN_VECS", int),
    "dedup_threshold": ("DEDUP_THRESHOLD", float),
    "image_retention_days": ("IMAGE_RETENTION_DAYS", int),
    "recognition_log_cooldown_minutes": ("RECOGNITION_LOG_COOLDOWN_MINUTES", int),
    "event_tablet_lookahead_minutes": ("EVENT_TABLET_LOOKAHEAD_MINUTES", int),
}


def get_default_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings(
        sure_threshold=settings.SURE_THRESHOLD,
        review_low=settings.REVIEW_LOW,
        gap_min=settings.GAP_MIN,
        upsert_score_max=settings.UPSERT_SCORE_MAX,
        upsert_min_vecs=settings.UPSERT_MIN_VECS,
        dedup_threshold=settings.DEDUP_THRESHOLD,
        image_retention_days=settings.IMAGE_RETENTION_DAYS,
        recognition_log_cooldown_minutes=settings.RECOGNITION_LOG_COOLDOWN_MINUTES,
        event_tablet_lookahead_minutes=settings.EVENT_TABLET_LOOKAHEAD_MINUTES,
    )


async def get_runtime_settings(db: AsyncSession) -> RuntimeSettings:
    current = get_default_runtime_settings()
    records = await repository.list_system_setting_records(db)

    for record in records:
        definition = SETTING_DEFINITIONS.get(record.key)
        if not definition:
            continue
        _, cast_type = definition
        setattr(current, record.key, cast_type(record.value))

    return current
