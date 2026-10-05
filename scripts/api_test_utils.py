"""Shared helpers for API test scripts."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.seed_data.constants import ADMIN_PASSWORD, ADMIN_USERNAME, EMPLOYEES, EMPLOYEE_PASSWORD


@dataclass
class ApiConfig:
    base_url: str
    username: str
    password: str


def normalize_base_url(raw: str) -> str:
    return raw.rstrip("/")


def load_config() -> ApiConfig:
    return ApiConfig(
        base_url=normalize_base_url(os.getenv("API_BASE_URL", "http://localhost:8000/api")),
        username=os.getenv("ADMIN_USERNAME", ADMIN_USERNAME),
        password=os.getenv("ADMIN_PASSWORD", ADMIN_PASSWORD),
    )


def load_employee_config() -> ApiConfig:
    default_username = EMPLOYEES[0]["username"] if EMPLOYEES else "an"
    return ApiConfig(
        base_url=normalize_base_url(os.getenv("API_BASE_URL", "http://localhost:8000/api")),
        username=os.getenv("EMPLOYEE_USERNAME", default_username),
        password=os.getenv("EMPLOYEE_PASSWORD", EMPLOYEE_PASSWORD),
    )


def _parse_json(text: str | None) -> Any:
    if not text:
        return None
    return json.loads(text)


def api_request_json(
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


def api_request_text(
    method: str,
    base_url: str,
    path: str,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> tuple[int, str, dict[str, str]]:
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
            return response.status, body, dict(response.headers)
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        details = body if body else exc.reason
        raise RuntimeError(f"{method} {url} failed: {exc.code} {details}") from exc


def login(config: ApiConfig) -> str:
    status, body = api_request_json(
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


def date_range(days_back: int = 7) -> tuple[date, date]:
    today = date.today()
    start = today - timedelta(days=days_back)
    return start, today
