from modules.admin.schemas import CleanupRunResponse
from infrastructure.cleanup import cleanup_old_images


async def run_manual_cleanup() -> CleanupRunResponse:
    """Chay cleanup anh ngay lap tuc de admin chu dong don anh qua han khi can."""
    summary = await cleanup_old_images()
    return CleanupRunResponse(
        success=True,
        deleted_recognition_log_images=summary["deleted_recognition_log_images"],
        deleted_resolved_unknown_queue=summary["deleted_resolved_unknown_queue"],
        deleted_orphan_qdrant_points=summary["deleted_orphan_qdrant_points"],
        deleted_unreferenced_files=summary["deleted_unreferenced_files"],
        auto_rejected_pending_recognition_logs=summary["auto_rejected_pending_recognition_logs"],
        deleted_rejected_recognition_logs=summary["deleted_rejected_recognition_logs"],
        deleted_read_notifications=summary["deleted_read_notifications"],
        deleted_empty_storage_dirs=summary["deleted_empty_storage_dirs"],
        retention_days=summary["retention_days"],
    )
