#!/usr/bin/env python3
"""Simple performance test script for the AI server.

Examples (PowerShell):
    python .\scripts\perf_ai_server.py detect --image .\tests\assets\face.jpg -n 100 -c 10
    python .\scripts\perf_ai_server.py recognise --image .\tests\assets\face.jpg -n 50 -c 5
    python .\scripts\perf_ai_server.py embed --image .\tests\assets\face.jpg -n 100 -c 10
    python .\scripts\perf_ai_server.py health -n 200 -c 20
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class Result:
    ok: bool
    status: Optional[int]
    elapsed_ms: float
    error: Optional[str] = None


@dataclass(frozen=True)
class Defaults:
    host: str = "172.16.75.66"
    detect_port: int = 8000
    embed_port: int = 8001
    prefix: str = "/api/v1"
    timeout: int = 10


def build_multipart(fields: Dict[str, str], files: Dict[str, Tuple[str, bytes, str]]) -> Tuple[bytes, str]:
    boundary = "----perfBoundary%f" % time.time()
    lines: List[bytes] = []

    for name, value in fields.items():
        lines.append(b"--" + boundary.encode("ascii"))
        lines.append(('Content-Disposition: form-data; name="%s"\r\n\r\n%s' % (name, value)).encode("utf-8"))

    for name, (filename, content, content_type) in files.items():
        lines.append(b"--" + boundary.encode("ascii"))
        lines.append(('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (name, filename)).encode("utf-8"))
        lines.append(("Content-Type: %s\r\n\r\n" % content_type).encode("utf-8"))
        lines.append(content)

    lines.append(b"--" + boundary.encode("ascii") + b"--\r\n")
    body = b"\r\n".join(lines)
    return body, "multipart/form-data; boundary=%s" % boundary


def http_request(method: str, url: str, headers: Dict[str, str], body: Optional[bytes], timeout: int) -> Result:
    start = time.perf_counter()
    req = urllib.request.Request(url, method=method, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            _ = resp.read()
            return Result(True, resp.status, (time.perf_counter() - start) * 1000)
    except urllib.error.HTTPError as exc:
        return Result(False, exc.code, (time.perf_counter() - start) * 1000, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return Result(False, None, (time.perf_counter() - start) * 1000, error=str(exc))


def run_workers(make_request, total: int, concurrency: int) -> List[Result]:
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request) for _ in range(total)]
        return [future.result() for future in as_completed(futures)]


def summarize(results: Iterable[Result], started_at: float) -> None:
    results_list = list(results)
    total = len(results_list)
    if total == 0:
        print("No results")
        return

    ok_count = sum(1 for r in results_list if r.ok)
    fail_count = total - ok_count
    elapsed_s = max(time.time() - started_at, 0.001)

    latencies = [r.elapsed_ms for r in results_list]
    latencies_sorted = sorted(latencies)

    def pct(p: float) -> float:
        if not latencies_sorted:
            return 0.0
        k = int(round((p / 100.0) * (len(latencies_sorted) - 1)))
        return latencies_sorted[k]

    status_counts: Dict[str, int] = {}
    for r in results_list:
        key = str(r.status) if r.status is not None else "error"
        status_counts[key] = status_counts.get(key, 0) + 1

    print("=== Summary ===")
    print("Total: %d | Success: %d | Fail: %d" % (total, ok_count, fail_count))
    print("RPS: %.2f" % (total / elapsed_s))
    print("Latency (ms): avg=%.2f min=%.2f max=%.2f" % (
        statistics.mean(latencies),
        min(latencies),
        max(latencies),
    ))
    print("p50=%.2f p90=%.2f p95=%.2f p99=%.2f" % (
        pct(50),
        pct(90),
        pct(95),
        pct(99),
    ))
    print("Status counts: %s" % json.dumps(status_counts, ensure_ascii=True))


def add_common_args(parser: argparse.ArgumentParser, defaults: Defaults) -> None:
    parser.add_argument("-n", "--requests", type=int, default=50, help="Total requests")
    parser.add_argument("-c", "--concurrency", type=int, default=5, help="Concurrent workers")
    parser.add_argument("--host", default=defaults.host, help="Target host")
    parser.add_argument("--prefix", default=defaults.prefix, help="API prefix")
    parser.add_argument("--timeout", type=int, default=defaults.timeout, help="Timeout seconds")


def build_base_url(host: str, port: int) -> str:
    return "http://%s:%d" % (host, port)


def normalize_prefix(prefix: str) -> str:
    if not prefix:
        return ""
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    return prefix.rstrip("/")


def build_url(base_url: str, prefix: str, path: str) -> str:
    normalized_prefix = normalize_prefix(prefix)
    if path == "/":
        normalized_path = "/"
    elif path.startswith("/"):
        normalized_path = path
    else:
        normalized_path = "/" + path
    return base_url + normalized_prefix + normalized_path


def ensure_file(path: str) -> bytes:
    if not path or not os.path.isfile(path):
        raise FileNotFoundError("Image file not found: %s" % path)
    with open(path, "rb") as f:
        return f.read()


def image_body(image_path: str) -> Tuple[bytes, str]:
    image_bytes = ensure_file(image_path)
    return build_multipart(
        fields={},
        files={"image": (os.path.basename(image_path), image_bytes, "image/jpeg")},
    )


def main() -> int:
    defaults = Defaults()
    parser = argparse.ArgumentParser(description="AI server performance test")
    sub = parser.add_subparsers(dest="command", required=True)

    detect = sub.add_parser("detect", help="POST /detect (multipart image)")
    add_common_args(detect, defaults)
    detect.add_argument("--image", required=True, help="Path to image file")
    detect.add_argument("--port", type=int, default=defaults.detect_port, help="Detection port")

    recognise = sub.add_parser("recognise", help="POST /recognise (base64)")
    add_common_args(recognise, defaults)
    recognise.add_argument("--image", required=True, help="Path to image file")
    recognise.add_argument("--port", type=int, default=defaults.detect_port, help="Detection port")
    recognise.add_argument("--camera-id", default="lobby-cam-01", help="Camera ID")

    embed = sub.add_parser("embed", help="POST /embed (multipart image)")
    add_common_args(embed, defaults)
    embed.add_argument("--image", required=True, help="Path to image file")
    embed.add_argument("--port", type=int, default=defaults.embed_port, help="Embedding port")

    health = sub.add_parser("health", help="GET /health")
    add_common_args(health, defaults)
    health.add_argument("--port", type=int, default=defaults.detect_port, help="Detection port")

    root = sub.add_parser("root", help="GET /")
    add_common_args(root, defaults)
    root.add_argument("--port", type=int, default=defaults.detect_port, help="Detection port")

    args = parser.parse_args()

    def make_request() -> Result:
        base_url = build_base_url(args.host, args.port)
        if args.command in {"health", "root"}:
            path = "health" if args.command == "health" else "/"
            url = build_url(base_url, args.prefix, path)
            return http_request("GET", url, {"accept": "application/json"}, None, args.timeout)
        if args.command in {"detect", "embed"}:
            body, content_type = image_body(args.image)
            url = build_url(base_url, args.prefix, args.command)
            headers = {"accept": "application/json", "Content-Type": content_type}
            return http_request("POST", url, headers, body, args.timeout)
        if args.command == "recognise":
            image_bytes = ensure_file(args.image)
            b64 = base64.b64encode(image_bytes).decode("ascii")
            payload = {"image": "data:image/jpeg;base64,%s" % b64, "camera_id": args.camera_id}
            body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
            url = build_url(base_url, args.prefix, "recognise")
            headers = {"accept": "application/json", "Content-Type": "application/json"}
            return http_request("POST", url, headers, body, args.timeout)
        return Result(False, None, 0.0, error="Unknown command")

    total = int(args.requests)
    concurrency = max(1, int(args.concurrency))

    started_at = time.time()
    results = run_workers(make_request, total, concurrency)
    summarize(results, started_at)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted")
        raise SystemExit(130)
