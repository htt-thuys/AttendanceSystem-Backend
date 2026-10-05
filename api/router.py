from fastapi import APIRouter

from modules.auth.routes import router as auth_router
from modules.attendance.routes import router as attendance_router
from modules.cameras.routes import router as cameras_router
from modules.cleanup.routes import router as cleanup_router
from modules.confirm.routes import router as confirm_router
from modules.dashboard.routes import router as dashboard_router
from modules.employees.routes import router as employees_router
from modules.events.routes import router as events_router
from modules.export.routes import router as export_router
from modules.me.routes import router as me_router
from modules.meetings.routes import router as meetings_router
from modules.notifications.routes import router as notifications_router
from modules.recognition.routes import recognize_router
from modules.recognition_logs.routes import router as recognition_logs_router
from modules.settings.routes import router as settings_router
from modules.unknown_queue.routes import router as unknown_queue_router
from modules.users.routes import router as users_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(cameras_router, tags=["Cameras"])
router.include_router(attendance_router, tags=["Attendance"])
router.include_router(recognize_router, tags=["Recognition"])
router.include_router(confirm_router, tags=["Recognition"])
router.include_router(me_router, prefix="/me", tags=["Me"])
router.include_router(notifications_router, tags=["Notifications"])
router.include_router(events_router, tags=["Events"])
router.include_router(meetings_router, tags=["Meetings"])
router.include_router(unknown_queue_router, tags=["Unknown Queue"])
router.include_router(employees_router, tags=["Employees"])
router.include_router(users_router, tags=["Users"])
router.include_router(recognition_logs_router, tags=["Recognition Logs"])
router.include_router(settings_router, tags=["Settings"])
router.include_router(cleanup_router, tags=["Cleanup"])
router.include_router(dashboard_router, tags=["Dashboard"])
router.include_router(export_router, tags=["Export"])
