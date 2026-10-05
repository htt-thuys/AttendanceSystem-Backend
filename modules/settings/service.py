from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.settings.runtime_settings import (
    SETTING_DEFINITIONS,
    get_default_runtime_settings,
    get_runtime_settings,
)
from infrastructure.database.models import SystemSetting
from modules.admin.schemas import RuntimeSettingsResponse, RuntimeSettingsUpdateRequest
from modules.settings import repository


async def get_admin_settings(db: AsyncSession) -> RuntimeSettingsResponse:
    """Lay toan bo setting runtime hien hanh ma server dang su dung."""
    runtime = await get_runtime_settings(db)
    return RuntimeSettingsResponse(
        sure_threshold=runtime.sure_threshold,
        review_low=runtime.review_low,
        gap_min=runtime.gap_min,
        upsert_score_max=runtime.upsert_score_max,
        upsert_min_vecs=runtime.upsert_min_vecs,
        dedup_threshold=runtime.dedup_threshold,
        image_retention_days=runtime.image_retention_days,
        recognition_log_cooldown_minutes=runtime.recognition_log_cooldown_minutes,
        event_tablet_lookahead_minutes=runtime.event_tablet_lookahead_minutes,
    )


async def update_admin_settings(
    db: AsyncSession,
    payload: RuntimeSettingsUpdateRequest,
) -> RuntimeSettingsResponse:
    """Cap nhat cac setting runtime do admin chinh truc tiep tu giao dien."""
    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        await _upsert_system_setting(db=db, key=key, value=value)
    await db.commit()
    return await get_admin_settings(db)


async def reset_admin_settings(db: AsyncSession) -> RuntimeSettingsResponse:
    """Xoa toan bo override trong DB de runtime quay ve gia tri mac dinh tu .env."""
    await repository.delete_all_system_setting_records(db)
    await db.commit()
    defaults = get_default_runtime_settings()
    return RuntimeSettingsResponse(
        sure_threshold=defaults.sure_threshold,
        review_low=defaults.review_low,
        gap_min=defaults.gap_min,
        upsert_score_max=defaults.upsert_score_max,
        upsert_min_vecs=defaults.upsert_min_vecs,
        dedup_threshold=defaults.dedup_threshold,
        image_retention_days=defaults.image_retention_days,
        recognition_log_cooldown_minutes=defaults.recognition_log_cooldown_minutes,
        event_tablet_lookahead_minutes=defaults.event_tablet_lookahead_minutes,
    )


async def _upsert_system_setting(db: AsyncSession, key: str, value: float | int) -> None:
    """Ghi de mot setting runtime vao DB de server doc gia tri moi ma khong can restart."""
    if key not in SETTING_DEFINITIONS:
        return

    record = await repository.get_system_setting_record(db, key)
    if record:
        record.value = str(value)
        record.updated_by = None
    else:
        db.add(SystemSetting(key=key, value=str(value), updated_by=None))
    await db.flush()
