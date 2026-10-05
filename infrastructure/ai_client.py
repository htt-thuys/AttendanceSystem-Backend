from typing import Any

import json
import httpx

from core.config import settings


DEFAULT_TIMEOUT = 10


class AIClientError(Exception):
    """Base error for AI service integration failures."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AIInvalidImageError(AIClientError):
    """Raised when the AI service rejects the uploaded image."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


def _build_url(path: str) -> str:
    prefix = settings.AI_SERVER_PREFIX or ""
    if prefix and not prefix.startswith("/"):
        prefix = "/" + prefix
    prefix = prefix.rstrip("/")

    if not path.startswith("/"):
        path = "/" + path

    return "http://%s:%d%s%s" % (
        settings.AI_SERVER_HOST,
        settings.AI_SERVER_EMBED_PORT,
        prefix,
        path,
    )


def _build_image_file(
    image_bytes: bytes,
    filename: str,
    content_type: str,
) -> dict:
    return {
        "image": (
            filename or "image.jpg",
            image_bytes,
            content_type or "image/jpeg",
        )
    }


def _pick_best_face(faces: list[dict]) -> dict | None:
    if not faces:
        return None
    return max(
        faces,
        key=lambda face: (
            (face.get("bbox", {}).get("x2", 0) - face.get("bbox", {}).get("x1", 0))
            * (face.get("bbox", {}).get("y2", 0) - face.get("bbox", {}).get("y1", 0))
        ),
    )


def _landmarks_to_json(landmarks: list[dict] | list[list[float]]) -> str:
    normalized = []
    for landmark in landmarks:
        if isinstance(landmark, dict):
            normalized.append([landmark["x"], landmark["y"]])
        else:
            normalized.append([landmark[0], landmark[1]])
    return json.dumps(normalized)


def _extract_face_data(data: Any) -> dict | None:
    if not isinstance(data, dict):
        raise AIClientError("AI server returned an invalid response")

    status = data.get("status") or data.get("label")
    if status == "no_face":
        return None
    if status == "invalid_image":
        raise AIInvalidImageError(data.get("message") or "Invalid image")
    if status == "spoof_detected":
        return {
            "spoof": True,
            "live_score": data.get("live_score"),
            "spoof_score": data.get("spoof_score"),
            "det_score": data.get("det_score"),
        }

    vector = data.get("vector") or data.get("embedding")
    if vector is None and isinstance(data.get("data"), dict):
        inner = data["data"]
        vector = inner.get("vector") or inner.get("embedding")

    if vector is None:
        raise AIClientError("AI server response does not include an embedding")

    face_quality = data.get("face_quality")
    if face_quality is None:
        face_quality = data.get("quality")
    if face_quality is None:
        face_quality = data.get("face_score")

    det_score = data.get("det_score")
    if det_score is None and isinstance(data.get("data"), dict):
        det_score = data["data"].get("det_score")
    if face_quality is None:
        face_quality = det_score

    return {
        "vector": vector,
        "face_quality": face_quality,
        "det_score": det_score,
    }


def _parse_detect_response(data: Any) -> dict | None:
    if not isinstance(data, dict):
        raise AIClientError("AI detect returned an invalid response")

    status = data.get("status") or data.get("label")
    if status == "no_face":
        return None
    if status == "invalid_image":
        raise AIInvalidImageError(data.get("message") or "Invalid image")
    if status != "ok":
        raise AIClientError(f"AI detect returned unexpected status: {status}")

    faces = data.get("faces") or []
    best_face = _pick_best_face(faces)
    if best_face is None:
        return None
    if not best_face.get("landmarks"):
        raise AIClientError("AI detect response does not include landmarks")

    return best_face


async def extract_face_data(
    image_bytes: bytes,
    filename: str = "image.jpg",
    content_type: str = "image/jpeg",
) -> dict | None:
    """Call AI service detect -> embed and return normalized face data."""
    timeout = settings.AI_SERVER_TIMEOUT or DEFAULT_TIMEOUT
    files = _build_image_file(image_bytes, filename, content_type)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            detect_response = await client.post(
                _build_url("/detect"),
                files=files,
                headers={"accept": "application/json"},
            )
            if detect_response.status_code >= 500:
                raise AIClientError(
                    f"AI detect error {detect_response.status_code}: {detect_response.text[:300]}"
                )
            if detect_response.status_code >= 400:
                raise AIInvalidImageError(
                    f"AI detect rejected image {detect_response.status_code}: {detect_response.text[:300]}"
                )
            try:
                detect_data = detect_response.json()
            except ValueError as exc:
                raise AIClientError("AI detect returned non-JSON response") from exc

            best_face = _parse_detect_response(detect_data)
            if best_face is None:
                return None

            embed_response = await client.post(
                _build_url("/embed"),
                files=files,
                data={"landmarks": _landmarks_to_json(best_face["landmarks"])},
                headers={"accept": "application/json"},
            )
    except httpx.RequestError as exc:
        raise AIClientError(f"Cannot connect to AI server: {exc}") from exc

    if embed_response.status_code >= 500:
        raise AIClientError(f"AI embed error {embed_response.status_code}: {embed_response.text[:300]}")
    if embed_response.status_code >= 400:
        raise AIInvalidImageError(
            f"AI embed rejected image {embed_response.status_code}: {embed_response.text[:300]}"
        )

    try:
        data = embed_response.json()
    except ValueError as exc:
        raise AIClientError("AI embed returned non-JSON response") from exc

    face_data = _extract_face_data(data)
    if face_data is not None and face_data.get("det_score") is None:
        face_data["det_score"] = best_face.get("det_score")
    if face_data is not None and face_data.get("face_quality") is None:
        face_data["face_quality"] = best_face.get("det_score")
    return face_data
