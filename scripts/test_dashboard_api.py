"""Standalone script to exercise Dashboard APIs via HTTP.

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

from scripts.api_test_utils import api_request_json, date_range, load_config, login


def main() -> None:
    config = load_config()

    print("Logging in as admin...")
    token = login(config)
    print("OK")

    date_from, date_to = date_range(days_back=7)

    print("Dashboard: stats...")
    status, stats = api_request_json(
        "GET",
        config.base_url,
        "/dashboard/stats",
        token=token,
    )
    if status != 200 or not isinstance(stats, dict):
        raise RuntimeError("Dashboard stats failed")
    print("OK")

    print("Dashboard: attendance trend...")
    status, trend = api_request_json(
        "GET",
        config.base_url,
        "/dashboard/attendance-trend",
        token=token,
        params={"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
    )
    if status != 200 or not isinstance(trend, dict):
        raise RuntimeError("Dashboard attendance trend failed")
    print("OK")

    print("Dashboard: recognition activity...")
    status, activity = api_request_json(
        "GET",
        config.base_url,
        "/dashboard/recognition-activity",
        token=token,
        params={"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
    )
    if status != 200 or not isinstance(activity, dict):
        raise RuntimeError("Dashboard recognition activity failed")
    print("OK")

    print("Dashboard: late arrivals...")
    status, late = api_request_json(
        "GET",
        config.base_url,
        "/dashboard/late-arrivals",
        token=token,
        params={"target_date": date_to.isoformat()},
    )
    if status != 200 or not isinstance(late, dict):
        raise RuntimeError("Dashboard late arrivals failed")
    print("OK")

    print("Dashboard: camera status...")
    status, camera = api_request_json(
        "GET",
        config.base_url,
        "/dashboard/camera-status",
        token=token,
    )
    if status != 200 or not isinstance(camera, dict):
        raise RuntimeError("Dashboard camera status failed")
    print("OK")

    print("All dashboard API checks completed successfully.")


if __name__ == "__main__":
    main()
