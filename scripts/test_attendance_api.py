"""Standalone script to exercise Attendance APIs via HTTP.

Prereqs:
- API server running (default http://localhost:8000)
- Seeded admin + employees (use docker seed or seed script)

Env vars:
- API_BASE_URL (default http://localhost:8000/api)
- ADMIN_USERNAME (default admin)
- ADMIN_PASSWORD (default admin123)
- EMPLOYEE_USERNAME (default an)
- EMPLOYEE_PASSWORD (default employee123)
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.api_test_utils import (
    api_request_json,
    api_request_text,
    date_range,
    load_config,
    load_employee_config,
    login,
)


def main() -> None:
    admin_config = load_config()
    employee_config = load_employee_config()

    print("Logging in as admin...")
    admin_token = login(admin_config)
    print("OK")

    print("Logging in as employee...")
    employee_token = login(employee_config)
    print("OK")

    date_from, date_to = date_range(days_back=7)

    print("Attendance: list records...")
    status, attendance = api_request_json(
        "GET",
        admin_config.base_url,
        "/attendance",
        token=admin_token,
        params={"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
    )
    if status != 200 or not isinstance(attendance, list):
        raise RuntimeError("List attendance failed")
    print(f"OK ({len(attendance)} records)")

    print("Attendance: today summary...")
    status, today_summary = api_request_json(
        "GET",
        admin_config.base_url,
        "/attendance/today",
        token=admin_token,
    )
    if status != 200 or not isinstance(today_summary, dict):
        raise RuntimeError("Attendance today summary failed")
    print("OK")

    print("Attendance: report...")
    status, report = api_request_json(
        "GET",
        admin_config.base_url,
        "/attendance/report",
        token=admin_token,
        params={"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
    )
    if status != 200 or not isinstance(report, dict):
        raise RuntimeError("Attendance report failed")
    print("OK")

    print("Attendance: my attendance...")
    status, my_attendance = api_request_json(
        "GET",
        employee_config.base_url,
        "/me/attendance",
        token=employee_token,
        params={"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
    )
    if status != 200 or not isinstance(my_attendance, list):
        raise RuntimeError("My attendance failed")
    print(f"OK ({len(my_attendance)} records)")

    print("Attendance: export...")
    status, csv_body, headers = api_request_text(
        "POST",
        admin_config.base_url,
        "/attendance/export",
        token=admin_token,
        payload={"date_from": date_from.isoformat(), "date_to": date_to.isoformat(), "format": "csv"},
    )
    if status != 200 or not csv_body.strip():
        raise RuntimeError("Attendance export failed")
    if "content-disposition" not in {key.lower() for key in headers}:
        raise RuntimeError("Attendance export missing Content-Disposition")
    print("OK")

    print("All attendance API checks completed successfully.")


if __name__ == "__main__":
    main()
