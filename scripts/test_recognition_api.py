#!/usr/bin/env python3
r"""End-to-end test for backend /recognition endpoint.

Examples (PowerShell):
    python .\scripts\test_recognition_api.py --image .\tests\assets\face.jpg
    python .\scripts\test_recognition_api.py --image .\tests\assets\face.jpg --base-url http://localhost:8008
    python .\scripts\test_recognition_api.py --image .\tests\assets\face.jpg --camera-id 1
    python .\scripts\test_recognition_api.py --image .\tests\assets\face.jpg --camera-id 1 --meeting-id 2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, Tuple


def build_multipart(fields: Dict[str, str], files: Dict[str, Tuple[str, bytes, str]]) -> Tuple[bytes, str]:
    boundary = "----backendBoundary%f" % time.time()
    lines = []

    for name, value in fields.items():
        lines.append(b"--" + boundary.encode("ascii"))
        lines.append(("Content-Disposition: form-data; name=\"%s\"" % name).encode("utf-8"))
        lines.append(b"")
        lines.append(str(value).encode("utf-8"))

    for name, (filename, content, content_type) in files.items():
        lines.append(b"--" + boundary.encode("ascii"))
        lines.append(
            ("Content-Disposition: form-data; name=\"%s\"; filename=\"%s\"" % (name, filename)).encode(
                "utf-8"
            )
        )
        lines.append(("Content-Type: %s" % content_type).encode("utf-8"))
        lines.append(b"")
        lines.append(content)

    lines.append(b"--" + boundary.encode("ascii") + b"--\r\n")
    body = b"\r\n".join(lines)
    return body, "multipart/form-data; boundary=%s" % boundary


def ensure_file(path: str) -> bytes:
    if not path or not os.path.isfile(path):
        raise FileNotFoundError("Image file not found: %s" % path)
    with open(path, "rb") as f:
        return f.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Test backend /recognition endpoint")
    parser.add_argument("--image", required=True, help="Path to image file")
    parser.add_argument("--camera-id", default="", help="Camera ID (optional)")
    parser.add_argument("--meeting-id", default="", help="Meeting ID selected by the frontend (optional)")
    parser.add_argument(
        "--base-url",
        default=os.getenv("BACKEND_BASE_URL", "http://localhost:8000"),
        help="Backend base URL, e.g. http://localhost:8000",
    )
    parser.add_argument(
        "--api-prefix",
        default=os.getenv("BACKEND_API_PREFIX", "/api"),
        help="API prefix, e.g. /api",
    )
    parser.add_argument("--timeout", type=int, default=20, help="Timeout seconds")
    args = parser.parse_args()

    image_bytes = ensure_file(args.image)
    body, content_type = build_multipart(
        fields={
            "camera_id": str(args.camera_id) if args.camera_id is not None else "",
            "meeting_id": str(args.meeting_id) if args.meeting_id is not None else "",
        },
        files={"image": (os.path.basename(args.image), image_bytes, "image/jpeg")},
    )

    api_prefix = args.api_prefix or ""
    if api_prefix and not api_prefix.startswith("/"):
        api_prefix = "/" + api_prefix
    api_prefix = api_prefix.rstrip("/")

    url = args.base_url.rstrip("/") + api_prefix + "/recognition"
    headers = {"accept": "application/json", "Content-Type": content_type}

    req = urllib.request.Request(url, method="POST", data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            payload = resp.read().decode("utf-8")
            data = json.loads(payload) if payload else {}
            print(json.dumps(data, ensure_ascii=True, indent=2))
            return 0
    except urllib.error.HTTPError as exc:
        print("HTTP error:", exc)
        if exc.fp is not None:
            print(exc.fp.read().decode("utf-8"))
        return 1
    except Exception as exc:  # noqa: BLE001
        print("Request failed:", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
