"""Public attendance service API.

Giữ nguyên interface cho routes/service consumers bằng cách re-export
các hàm từ các service nhỏ hơn.
"""

from .action_service import admin_update_attendance, request_absence
from .query_service import (
    export_attendance,
    get_report,
    get_today_summary,
    list_attendance,
    list_my_attendance,
)
from .sync_service import record_auto_attendance

__all__ = [
    "admin_update_attendance",
    "export_attendance",
    "get_report",
    "get_today_summary",
    "list_attendance",
    "list_my_attendance",
    "record_auto_attendance",
    "request_absence",
]
