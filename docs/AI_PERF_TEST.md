# AI Performance Test Guide

This guide explains how to run a quick performance test for the AI server using the script in scripts/perf_ai_server.py.

## 1) Prerequisites

- Python 3.10+ and dependencies installed from requirements.txt
- Access to the AI server:
  - Detection service: http://172.16.75.66:8000
  - Embedding service: http://172.16.75.66:8001
- One or more test images (JPG/PNG)

## 2) Quick Commands (PowerShell)

Health check (GET /api/v1/health):

```
python .\scripts\perf_ai_server.py health -n 200 -c 20
```

Detect faces (POST /api/v1/detect):

```
python .\scripts\perf_ai_server.py detect --image .\path\to\face.jpg -n 100 -c 10
```

Recognise (POST /api/v1/recognise, note spelling: recognise):

```
python .\scripts\perf_ai_server.py recognise --image .\path\to\face.jpg -n 50 -c 5 --camera-id lobby-cam-01
```

Embed (POST /api/v1/embed):

```
python .\scripts\perf_ai_server.py embed --image .\path\to\face.jpg -n 100 -c 10
```

## 3) Parameters

- -n, --requests: total number of requests
- -c, --concurrency: number of concurrent workers
- --host: target host (default 172.16.75.66)
- --port: target port (default 8000 for detect/recognise/health, 8001 for embed)
- --prefix: API prefix (default /api/v1)
- --timeout: request timeout in seconds (default 10)

## 4) Testing When Hosted on Docker

If the AI server runs in Docker, use the host and ports that are published by Docker.

Common cases:

- Run on the same machine (Docker Desktop):
  - Use --host 127.0.0.1 (or localhost)
  - Use the published ports from docker-compose.yml or Docker run -p mapping

Example (ports 8000 and 8001 are published):

```
python .\scripts\perf_ai_server.py health --host 127.0.0.1 --port 8000 -n 200 -c 20
python .\scripts\perf_ai_server.py detect --host 127.0.0.1 --port 8000 --image .\path\to\face.jpg -n 100 -c 10
python .\scripts\perf_ai_server.py embed --host 127.0.0.1 --port 8001 --image .\path\to\face.jpg -n 100 -c 10
```

- Run on a remote Docker host:
  - Use --host <docker-host-ip>
  - Use the published ports on that host

## 5) Output Interpretation

The script prints a summary:

- Total / Success / Fail
- RPS (requests per second)
- Latency stats: avg, min, max, p50, p90, p95, p99
- Status code counts

Example:

```
=== Summary ===
Total: 100 | Success: 98 | Fail: 2
RPS: 18.42
Latency (ms): avg=42.31 min=18.21 max=120.05
p50=39.12 p90=71.22 p95=88.20 p99=115.02
Status counts: {"200": 98, "500": 2}
```

## 6) Notes

- If you see many 503 errors, the AI server may not be ready or is missing model weights.
- Use smaller images to reduce latency during load tests.
- Increase concurrency gradually to avoid saturating the server.
