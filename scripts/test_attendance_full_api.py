"""Comprehensive HTTP checks for attendance and meeting attendance APIs.

Prereqs:
- API server running (default http://localhost:8000/api)
- Seeded admin + employees (use docker seed or scripts/seed_test_data.py)

Env vars:
- API_BASE_URL (default http://localhost:8000/api)
- ADMIN_USERNAME (default admin)
- ADMIN_PASSWORD (default admin123)
- EMPLOYEE_USERNAME (default first seeded employee)
- SECOND_EMPLOYEE_USERNAME (default second seeded employee)
- EMPLOYEE_PASSWORD (default employee123)
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.seed_data.constants import ADMIN_PASSWORD, ADMIN_USERNAME, EMPLOYEE_PASSWORD, EMPLOYEES


@dataclass
class ApiConfig:
    base_url: str
    admin_username: str
    admin_password: str
    employee_username: str
    second_employee_username: str
    employee_password: str


@dataclass
class ApiResult:
    status: int
    body: Any


def load_config() -> ApiConfig:
    first_employee = EMPLOYEES[0]["username"] if len(EMPLOYEES) > 0 else "an"
    second_employee = EMPLOYEES[1]["username"] if len(EMPLOYEES) > 1 else "binh"
    return ApiConfig(
        base_url=os.getenv("API_BASE_URL", "http://localhost:8000/api").rstrip("/"),
        admin_username=os.getenv("ADMIN_USERNAME", ADMIN_USERNAME),
        admin_password=os.getenv("ADMIN_PASSWORD", ADMIN_PASSWORD),
        employee_username=os.getenv("EMPLOYEE_USERNAME", first_employee),
        second_employee_username=os.getenv("SECOND_EMPLOYEE_USERNAME", second_employee),
        employee_password=os.getenv("EMPLOYEE_PASSWORD", EMPLOYEE_PASSWORD),
    )


def parse_body(raw: str) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def request_json(
    method: str,
    base_url: str,
    path: str,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> ApiResult:
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
            return ApiResult(response.status, parse_body(response.read().decode("utf-8")))
    except HTTPError as exc:
        return ApiResult(exc.code, parse_body(exc.read().decode("utf-8")))


def expect(
    name: str,
    result: ApiResult,
    expected_status: int,
    validate: Callable[[Any], None] | None = None,
) -> Any:
    if result.status != expected_status:
        raise RuntimeError(f"{name}: expected {expected_status}, got {result.status}: {result.body}")
    if validate:
        validate(result.body)
    print(f"OK - {name}")
    return result.body


def require_dict(body: Any) -> None:
    if not isinstance(body, dict):
        raise RuntimeError(f"Expected dict body, got {type(body).__name__}: {body}")


def require_list(body: Any) -> None:
    if not isinstance(body, list):
        raise RuntimeError(f"Expected list body, got {type(body).__name__}: {body}")


def require_success(body: Any) -> None:
    require_dict(body)
    if not body.get("success"):
        raise RuntimeError(f"Expected success=true, got: {body}")


def login(base_url: str, username: str, password: str) -> str:
    result = request_json("POST", base_url, "/auth/login", payload={"username": username, "password": password})
    body = expect(f"login {username}", result, 200, require_dict)
    token = body.get("access_token")
    if not token:
        raise RuntimeError(f"Login for {username} did not return access_token")
    return token


def get_profile(base_url: str, token: str, label: str) -> dict[str, Any]:
    body = expect(f"{label}: get profile", request_json("GET", base_url, "/me/profile", token=token), 200, require_dict)
    if not body.get("employee_id"):
        raise RuntimeError(f"{label} account must be linked to an employee")
    return body


def create_meeting(base_url: str, admin_token: str, title: str) -> int:
    now = datetime.now(timezone.utc)
    result = request_json(
        "POST",
        base_url,
        "/meetings",
        token=admin_token,
        payload={
            "title": title,
            "description": "Created by test_attendance_full_api.py",
            "scheduled_start": (now - timedelta(minutes=5)).isoformat(),
            "scheduled_end": (now + timedelta(hours=1)).isoformat(),
            "location": "API Test Room",
        },
    )
    body = expect(f"{title}: create meeting", result, 200, require_dict)
    meeting_id = body.get("id")
    if not meeting_id:
        raise RuntimeError(f"{title}: create meeting did not return id")
    return int(meeting_id)


def add_participants(base_url: str, admin_token: str, meeting_id: int, employee_ids: list[int]) -> None:
    expect(
        f"meeting {meeting_id}: add participants {employee_ids}",
        request_json(
            "POST",
            base_url,
            f"/meetings/{meeting_id}/participants",
            token=admin_token,
            payload={"employee_ids": employee_ids},
        ),
        200,
        require_success,
    )


def update_meeting_status(base_url: str, admin_token: str, meeting_id: int, status: str) -> None:
    expect(
        f"meeting {meeting_id}: update status to {status}",
        request_json("PATCH", base_url, f"/meetings/{meeting_id}", token=admin_token, payload={"status": status}),
        200,
        require_dict,
    )


def cancel_meeting(base_url: str, admin_token: str, meeting_id: int) -> None:
    expect(
        f"meeting {meeting_id}: cancel",
        request_json("DELETE", base_url, f"/meetings/{meeting_id}", token=admin_token),
        200,
        require_success,
    )


def assert_meeting_attendance_counts(body: Any, present: int, invited: int) -> None:
    require_dict(body)
    actual_present = body.get("present_count", 0) + body.get("late_count", 0)
    if actual_present != present or body.get("invited_count") != invited:
        raise RuntimeError(f"Unexpected meeting attendance counts: {body}")


def run_meeting_attendance_cases(config: ApiConfig, admin_token: str, employee_token: str, second_token: str) -> None:
    employee_profile = get_profile(config.base_url, employee_token, "employee")
    second_profile = get_profile(config.base_url, second_token, "second employee")
    employee_id = int(employee_profile["employee_id"])
    second_employee_id = int(second_profile["employee_id"])

    meeting_id = create_meeting(config.base_url, admin_token, "API Full Attendance - main")
    add_participants(config.base_url, admin_token, meeting_id, [employee_id])

    expect(
        "self check-in without token is rejected",
        request_json("POST", config.base_url, f"/me/meetings/{meeting_id}/checkin"),
        401,
        require_dict,
    )
    expect(
        "admin without employee link cannot self check-in",
        request_json("POST", config.base_url, f"/me/meetings/{meeting_id}/checkin", token=admin_token),
        400,
        require_dict,
    )
    expect(
        "non-participant self check-in succeeds (auto-added)",
        request_json("POST", config.base_url, f"/me/meetings/{meeting_id}/checkin", token=second_token),
        200,
        require_success,
    )
    expect(
        "participant self check-in succeeds",
        request_json(
            "POST",
            config.base_url,
            f"/me/meetings/{meeting_id}/checkin",
            token=employee_token,
            payload={"note": "first check-in"},
        ),
        200,
        require_success,
    )
    expect(
        "duplicate self check-in is rejected",
        request_json("POST", config.base_url, f"/me/meetings/{meeting_id}/checkin", token=employee_token),
        400,
        require_dict,
    )
    expect(
        "meeting attendance reflects present participant",
        request_json("GET", config.base_url, f"/meetings/{meeting_id}/attendance", token=admin_token),
        200,
        lambda body: assert_meeting_attendance_counts(body, present=2, invited=0),
    )
    expect(
        "participant self check-out succeeds",
        request_json(
            "POST",
            config.base_url,
            f"/me/meetings/{meeting_id}/checkout",
            token=employee_token,
            payload={"note": "leaving meeting"},
        ),
        200,
        require_success,
    )
    expect(
        "duplicate self check-out is rejected",
        request_json("POST", config.base_url, f"/me/meetings/{meeting_id}/checkout", token=employee_token),
        400,
        require_dict,
    )
    no_checkin_meeting_id = create_meeting(config.base_url, admin_token, "API Full Attendance - checkout before checkin")
    add_participants(config.base_url, admin_token, no_checkin_meeting_id, [employee_id])
    update_meeting_status(config.base_url, admin_token, no_checkin_meeting_id, "in_progress")

    expect(
        "non-participant cannot self check-out",
        request_json("POST", config.base_url, f"/me/meetings/{no_checkin_meeting_id}/checkout", token=second_token),
        404,
        require_dict,
    )
    expect(
        "checkout before check-in is rejected",
        request_json("POST", config.base_url, f"/me/meetings/{no_checkin_meeting_id}/checkout", token=employee_token),
        400,
        require_dict,
    )

    cancelled_meeting_id = create_meeting(config.base_url, admin_token, "API Full Attendance - cancelled")
    add_participants(config.base_url, admin_token, cancelled_meeting_id, [employee_id])
    cancel_meeting(config.base_url, admin_token, cancelled_meeting_id)
    expect(
        "check-in to cancelled meeting is rejected",
        request_json("POST", config.base_url, f"/me/meetings/{cancelled_meeting_id}/checkin", token=employee_token),
        400,
        require_dict,
    )

    completed_meeting_id = create_meeting(config.base_url, admin_token, "API Full Attendance - completed")
    add_participants(config.base_url, admin_token, completed_meeting_id, [employee_id, second_employee_id])
    update_meeting_status(config.base_url, admin_token, completed_meeting_id, "completed")
    expect(
        "check-in to completed meeting is rejected",
        request_json("POST", config.base_url, f"/me/meetings/{completed_meeting_id}/checkin", token=employee_token),
        400,
        require_dict,
    )


def run_daily_attendance_cases(config: ApiConfig, admin_token: str, employee_token: str) -> None:
    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    expect(
        "admin can list attendance",
        request_json(
            "GET",
            config.base_url,
            "/attendance",
            token=admin_token,
            params={"date_from": yesterday.isoformat(), "date_to": today.isoformat()},
        ),
        200,
        require_list,
    )
    expect(
        "employee cannot list admin attendance",
        request_json("GET", config.base_url, "/attendance", token=employee_token),
        403,
        require_dict,
    )
    expect(
        "missing token cannot list admin attendance",
        request_json("GET", config.base_url, "/attendance"),
        401,
        require_dict,
    )
    expect(
        "invalid attendance status is rejected",
        request_json("GET", config.base_url, "/attendance", token=admin_token, params={"status": "bad_status"}),
        400,
        require_dict,
    )
    expect(
        "admin can get today summary",
        request_json("GET", config.base_url, "/attendance/today", token=admin_token),
        200,
        require_dict,
    )
    expect(
        "admin can get attendance report",
        request_json(
            "GET",
            config.base_url,
            "/attendance/report",
            token=admin_token,
            params={"date_from": yesterday.isoformat(), "date_to": today.isoformat()},
        ),
        200,
        require_dict,
    )
    expect(
        "report rejects reversed date range",
        request_json(
            "GET",
            config.base_url,
            "/attendance/report",
            token=admin_token,
            params={"date_from": tomorrow.isoformat(), "date_to": yesterday.isoformat()},
        ),
        400,
        require_dict,
    )
    expect(
        "employee can read own attendance",
        request_json(
            "GET",
            config.base_url,
            "/me/attendance",
            token=employee_token,
            params={"date_from": yesterday.isoformat(), "date_to": today.isoformat()},
        ),
        200,
        require_list,
    )
    expect(
        "missing token cannot read own attendance",
        request_json("GET", config.base_url, "/me/attendance"),
        401,
        require_dict,
    )
    expect(
        "attendance export csv succeeds",
        request_json(
            "POST",
            config.base_url,
            "/attendance/export",
            token=admin_token,
            payload={"date_from": yesterday.isoformat(), "date_to": today.isoformat(), "format": "csv"},
        ),
        200,
    )
    expect(
        "attendance export rejects unsupported format",
        request_json(
            "POST",
            config.base_url,
            "/attendance/export",
            token=admin_token,
            payload={"date_from": yesterday.isoformat(), "date_to": today.isoformat(), "format": "xlsx"},
        ),
        400,
        require_dict,
    )


def main() -> None:
    config = load_config()

    print("Logging in...")
    admin_token = login(config.base_url, config.admin_username, config.admin_password)
    employee_token = login(config.base_url, config.employee_username, config.employee_password)
    second_token = login(config.base_url, config.second_employee_username, config.employee_password)

    print("Running meeting attendance check-in/check-out cases...")
    run_meeting_attendance_cases(config, admin_token, employee_token, second_token)

    print("Running daily attendance API cases...")
    run_daily_attendance_cases(config, admin_token, employee_token)

    print("All comprehensive attendance API checks completed successfully.")


if __name__ == "__main__":
    main()
