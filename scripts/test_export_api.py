"""Standalone script to exercise Export APIs via HTTP.

Prereqs:
- API server running (default http://localhost:8000)
- Seeded admin + employees (use docker seed or seed script)

Env vars:
- API_BASE_URL (default http://localhost:8000/api)
- ADMIN_USERNAME (default admin)
- ADMIN_PASSWORD (default admin123)
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.api_test_utils import api_request_text, date_range, load_config, login


def main() -> None:
    config = load_config()

    print("Logging in as admin...")
    token = login(config)
    print("OK")

    date_from, date_to = date_range(days_back=7)

    print("Export: attendance...")
    status, attendance_export, _ = api_request_text(
        "POST",
        config.base_url,
        "/export/attendance",
        token=token,
        payload={"date_from": date_from.isoformat(), "date_to": date_to.isoformat(), "format": "csv"},
    )
    if status != 200 or not attendance_export.strip():
        raise RuntimeError("Export attendance failed")
    print("OK")

    print("Export: recognition logs...")
    status, logs_export, _ = api_request_text(
        "POST",
        config.base_url,
        "/export/recognition-logs",
        token=token,
        payload={"date_from": date_from.isoformat(), "date_to": date_to.isoformat(), "format": "csv"},
    )
    if status != 200 or not logs_export.strip():
        raise RuntimeError("Export recognition logs failed")
    print("OK")

    print("Export: employees...")
    status, employees_export, _ = api_request_text(
        "POST",
        config.base_url,
        "/export/employees",
        token=token,
        payload={"format": "csv"},
    )
    if status != 200 or not employees_export.strip():
        raise RuntimeError("Export employees failed")
    print("OK")

    print("All export API checks completed successfully.")


if __name__ == "__main__":
    main()
