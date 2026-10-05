import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, or_, select

from core.config import settings
from infrastructure.database.models import Employee, FaceVector, Notification, RecognitionLog, UnknownQueue
from infrastructure.database.session import AsyncSessionLocal
from infrastructure.settings.runtime_settings import get_runtime_settings
from infrastructure.vector_db.qdrant_client import delete_vectors, list_point_ids
from storage.image_store import delete_image, ensure_storage_dirs, normalize_relative_path


async def cleanup_old_images() -> dict[str, int]:
    ensure_storage_dirs()

    async with AsyncSessionLocal() as db:
        runtime_settings = await get_runtime_settings(db)
        retention_days = runtime_settings.image_retention_days
        cutoff = datetime.now() - timedelta(days=retention_days)
        protected_paths = await _load_protected_paths(db)
        deleted_recognition_log_images = await _cleanup_old_recognition_log_images(
            db=db,
            cutoff=cutoff,
            protected_paths=protected_paths,
        )
        deleted_resolved_unknown_queue = await _cleanup_resolved_unknown_queue(
            db=db,
            cutoff=cutoff,
        )
        auto_rejected_pending_recognition_logs = await _cleanup_pending_recognition_logs(
            db=db,
            cutoff=cutoff,
        )
        deleted_rejected_recognition_logs = await _cleanup_rejected_recognition_logs(
            db=db,
            cutoff=cutoff,
        )
        deleted_read_notifications = await _cleanup_read_notifications(
            db=db,
            cutoff=cutoff,
        )
        deleted_orphan_qdrant_points = await _cleanup_orphan_qdrant_points(db)
        await db.commit()

    deleted_unreferenced_files = _cleanup_unreferenced_files(
        cutoff=cutoff,
        protected_paths=protected_paths,
    )
    deleted_empty_storage_dirs = _cleanup_empty_storage_dirs()
    return {
        "deleted_recognition_log_images": deleted_recognition_log_images,
        "deleted_resolved_unknown_queue": deleted_resolved_unknown_queue,
        "auto_rejected_pending_recognition_logs": auto_rejected_pending_recognition_logs,
        "deleted_rejected_recognition_logs": deleted_rejected_recognition_logs,
        "deleted_read_notifications": deleted_read_notifications,
        "deleted_orphan_qdrant_points": deleted_orphan_qdrant_points,
        "deleted_unreferenced_files": deleted_unreferenced_files,
        "deleted_empty_storage_dirs": deleted_empty_storage_dirs,
        "retention_days": retention_days,
    }


async def run_periodic_cleanup() -> None:
    while True:
        try:
            await cleanup_old_images()
        except Exception as error:
            print(f"Loi cleanup anh dinh ky: {error}")
        await asyncio.sleep(settings.IMAGE_CLEANUP_INTERVAL_HOURS * 3600)


async def _load_protected_paths(db) -> set[str]:
    protected_paths: set[str] = set()

    avatar_result = await db.execute(select(Employee.avatar_path).where(Employee.avatar_path.is_not(None)))
    protected_paths.update(normalize_relative_path(path) for path in avatar_result.scalars().all() if path)

    vector_result = await db.execute(select(FaceVector.source_image_path).where(FaceVector.source_image_path.is_not(None)))
    protected_paths.update(normalize_relative_path(path) for path in vector_result.scalars().all() if path)

    unknown_result = await db.execute(
        select(UnknownQueue.image_path).where(
            UnknownQueue.resolved_at.is_(None),
            UnknownQueue.image_path.is_not(None),
        )
    )
    protected_paths.update(normalize_relative_path(path) for path in unknown_result.scalars().all() if path)

    return protected_paths


async def _cleanup_old_recognition_log_images(db, cutoff: datetime, protected_paths: set[str]) -> int:
    log_result = await db.execute(
        select(RecognitionLog).where(
            RecognitionLog.face_image_path.is_not(None),
            RecognitionLog.captured_at < cutoff,
        )
    )
    old_logs = list(log_result.scalars().all())
    deleted_count = 0

    for log_entry in old_logs:
        relative_path = normalize_relative_path(log_entry.face_image_path)
        if relative_path in protected_paths:
            continue
        await delete_image(relative_path)
        log_entry.face_image_path = None
        deleted_count += 1

    return deleted_count


async def _cleanup_resolved_unknown_queue(db, cutoff: datetime) -> int:
    result = await db.execute(
        select(UnknownQueue).where(
            UnknownQueue.resolved_at.is_not(None),
            UnknownQueue.resolved_at < cutoff,
        )
    )
    resolved_items = list(result.scalars().all())
    deleted_count = 0

    for item in resolved_items:
        await delete_image(item.image_path)
        await db.delete(item)
        deleted_count += 1

    return deleted_count


async def _cleanup_pending_recognition_logs(db, cutoff: datetime) -> int:
    result = await db.execute(
        select(RecognitionLog).where(
            RecognitionLog.result_label.in_(["sure", "review"]),
            RecognitionLog.final_label.is_(None),
            RecognitionLog.resolved_at.is_(None),
            RecognitionLog.captured_at < cutoff,
        )
    )
    pending_logs = list(result.scalars().all())
    for log_entry in pending_logs:
        log_entry.final_label = "rejected"
        log_entry.resolved_at = func.now()
    return len(pending_logs)


async def _cleanup_rejected_recognition_logs(db, cutoff: datetime) -> int:
    result = await db.execute(
        select(RecognitionLog).where(
            RecognitionLog.final_label == "rejected",
            RecognitionLog.employee_id.is_(None),
            RecognitionLog.face_image_path.is_(None),
            RecognitionLog.captured_at < cutoff,
        )
    )
    rejected_logs = list(result.scalars().all())
    for log_entry in rejected_logs:
        await db.delete(log_entry)
    return len(rejected_logs)


async def _cleanup_read_notifications(db, cutoff: datetime) -> int:
    result = await db.execute(
        select(Notification).where(
            Notification.is_read.is_(True),
            or_(
                Notification.read_at < cutoff,
                Notification.read_at.is_(None) & (Notification.created_at < cutoff),
            ),
        )
    )
    notifications = list(result.scalars().all())
    for notification in notifications:
        await db.delete(notification)
    return len(notifications)


async def _cleanup_orphan_qdrant_points(db) -> int:
    result = await db.execute(select(FaceVector.qdrant_point_id))
    valid_point_ids = {int(point_id) for point_id in result.scalars().all() if point_id is not None}
    existing_point_ids = set(list_point_ids())
    orphan_point_ids = sorted(existing_point_ids - valid_point_ids)
    delete_vectors(orphan_point_ids)
    return len(orphan_point_ids)


def _cleanup_unreferenced_files(cutoff: datetime, protected_paths: set[str]) -> int:
    root = Path(settings.IMAGE_STORAGE_PATH)
    if not root.exists():
        return 0

    deleted_count = 0
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue

        relative_path = normalize_relative_path(file_path.relative_to(root).as_posix())
        if relative_path in protected_paths:
            continue

        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        if file_mtime < cutoff:
            try:
                file_path.unlink()
                deleted_count += 1
            except OSError as error:
                print(f"Loi khi cleanup file {file_path}: {error}")

    return deleted_count


def _cleanup_empty_storage_dirs() -> int:
    root = Path(settings.IMAGE_STORAGE_PATH)
    if not root.exists():
        return 0

    deleted_count = 0
    for dir_path in sorted((path for path in root.rglob("*") if path.is_dir()), reverse=True):
        try:
            if dir_path == root:
                continue
            dir_path.rmdir()
            deleted_count += 1
        except OSError:
            continue
    return deleted_count
