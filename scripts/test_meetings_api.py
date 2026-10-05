"""Standalone script to exercise Meetings APIs via HTTP.

Prereqs:
- API server running (default http://localhost:8000)
- Seeded admin + employees (use docker seed or seed script)

Env vars:
- API_BASE_URL (default http://localhost:8000)
- ADMIN_USERNAME (default admin)
- ADMIN_PASSWORD (default admin123)
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.seed_data.constants import ADMIN_PASSWORD, ADMIN_USERNAME


@dataclass
class ApiConfig:
    base_url: str
    username: str
    password: str


def _normalize_base_url(raw: str) -> str:
    return raw.rstrip("/")


def _parse_json(text: str | None) -> Any:
    if not text:
        return None
    return json.loads(text)


def api_request(
    method: str,
    base_url: str,
    path: str,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    url = f"{base_url}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"

    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request) as response:
            body = response.read().decode("utf-8")
            return response.status, _parse_json(body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        details = body if body else exc.reason
        raise RuntimeError(f"{method} {url} failed: {exc.code} {details}") from exc


def login(config: ApiConfig) -> str:
    status, body = api_request(
        "POST",
        config.base_url,
        "/auth/login",
        payload={"username": config.username, "password": config.password},
    )
    if status != 200:
        raise RuntimeError(f"Login failed with status {status}")
    token = body.get("access_token") if isinstance(body, dict) else None
    if not token:
        raise RuntimeError("Login did not return access_token")
    return token


def list_employees(base_url: str, token: str) -> list[dict[str, Any]]:
    status, body = api_request("GET", base_url, "/employees", token=token)
    if status != 200:
        raise RuntimeError(f"List employees failed with status {status}")
    if not isinstance(body, list):
        raise RuntimeError("Employees response is not a list")
    return body


def main() -> None:
    config = ApiConfig(
        base_url=_normalize_base_url(os.getenv("API_BASE_URL", "http://localhost:8000/api")),
        username=os.getenv("ADMIN_USERNAME", ADMIN_USERNAME),
        password=os.getenv("ADMIN_PASSWORD", ADMIN_PASSWORD),
    )

    print("Logging in as admin...")
    token = login(config)
    print("OK")

    employees = list_employees(config.base_url, token)
    if len(employees) < 1:
        raise RuntimeError("No employees found. Seed data first.")
    employee_ids = [emp["id"] for emp in employees[:2]]

    now = datetime.now(timezone.utc)
    start_time = now + timedelta(hours=1)
    end_time = start_time + timedelta(hours=1)

    print("Creating meeting...")
    status, meeting = api_request(
        "POST",
        config.base_url,
        "/meetings",
        token=token,
        payload={
            "title": "API Test Meeting",
            "description": "Meeting created by test_meetings_api.py",
            "scheduled_start": start_time.isoformat(),
            "scheduled_end": end_time.isoformat(),
            "location": "Test Room",
        },
    )
    if status != 200 or not isinstance(meeting, dict):
        raise RuntimeError("Create meeting failed")
    meeting_id = meeting.get("id")
    if not meeting_id:
        raise RuntimeError("Create meeting did not return id")
    print(f"OK (id={meeting_id})")

    print("Listing meetings...")
    status, meetings = api_request(
        "GET",
        config.base_url,
        "/meetings",
        token=token,
        params={"date_from": start_time.date().isoformat()},
    )
    if status != 200 or not isinstance(meetings, list):
        raise RuntimeError("List meetings failed")
    print(f"OK ({len(meetings)} found)")

    print("Getting meeting detail...")
    status, detail = api_request(
        "GET",
        config.base_url,
        f"/meetings/{meeting_id}",
        token=token,
    )
    if status != 200 or not isinstance(detail, dict):
        raise RuntimeError("Get meeting detail failed")
    print("OK")

    print("Updating meeting...")
    status, updated = api_request(
        "PATCH",
        config.base_url,
        f"/meetings/{meeting_id}",
        token=token,
        payload={"title": "API Test Meeting (Updated)"},
    )
    if status != 200 or not isinstance(updated, dict):
        raise RuntimeError("Update meeting failed")
    print("OK")

    print("Adding participants...")
    status, added = api_request(
        "POST",
        config.base_url,
        f"/meetings/{meeting_id}/participants",
        token=token,
        payload={"employee_ids": employee_ids},
    )
    if status != 200 or not isinstance(added, dict) or not added.get("success"):
        raise RuntimeError("Add participants failed")
    print("OK")

    print("Getting attendance...")
    status, attendance = api_request(
        "GET",
        config.base_url,
        f"/meetings/{meeting_id}/attendance",
        token=token,
    )
    if status != 200 or not isinstance(attendance, dict):
        raise RuntimeError("Get attendance failed")
    print("OK")

    if employee_ids:
        print("Removing participant...")
        status, removed = api_request(
            "DELETE",
            config.base_url,
            f"/meetings/{meeting_id}/participants/{employee_ids[0]}",
            token=token,
        )
        if status != 200 or not isinstance(removed, dict) or not removed.get("success"):
            raise RuntimeError("Remove participant failed")
        print("OK")

    print("Canceling meeting...")
    status, canceled = api_request(
        "DELETE",
        config.base_url,
        f"/meetings/{meeting_id}",
        token=token,
    )
    if status != 200 or not isinstance(canceled, dict) or not canceled.get("success"):
        raise RuntimeError("Cancel meeting failed")
    print("OK")

    print("All meetings API checks completed successfully.")


if __name__ == "__main__":
    main()
