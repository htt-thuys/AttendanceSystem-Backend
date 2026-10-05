"""Standalone script to exercise Notifications APIs via HTTP.

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

from scripts.api_test_utils import api_request_json, load_config, login


def main() -> None:
    config = load_config()

    print("Logging in as admin...")
    token = login(config)
    print("OK")

    print("Notifications: list...")
    status, notif_list = api_request_json(
        "GET",
        config.base_url,
        "/me/notifications",
        token=token,
        params={"page": 1, "page_size": 10},
    )
    if status != 200 or not isinstance(notif_list, dict):
        raise RuntimeError("Notifications list failed")
    items = notif_list.get("items", []) if isinstance(notif_list, dict) else []
    print(f"OK ({len(items)} items)")

    print("Notifications: unread count...")
    status, unread = api_request_json(
        "GET",
        config.base_url,
        "/me/notifications/unread-count",
        token=token,
    )
    if status != 200 or not isinstance(unread, dict):
        raise RuntimeError("Notifications unread count failed")
    print("OK")

    if items:
        first_id = items[0].get("id")
        if first_id is not None:
            print("Notifications: mark one as read...")
            status, read_one = api_request_json(
                "PATCH",
                config.base_url,
                f"/me/notifications/{first_id}/read",
                token=token,
            )
            if status != 200 or not isinstance(read_one, dict) or not read_one.get("success"):
                raise RuntimeError("Notification mark read failed")
            print("OK")

    print("Notifications: mark all as read...")
    status, read_all = api_request_json(
        "POST",
        config.base_url,
        "/me/notifications/read-all",
        token=token,
        payload={"include_read": True},
    )
    if status != 200 or not isinstance(read_all, dict) or not read_all.get("success"):
        raise RuntimeError("Notification mark all read failed")
    print("OK")

    print("All notifications API checks completed successfully.")


if __name__ == "__main__":
    main()
