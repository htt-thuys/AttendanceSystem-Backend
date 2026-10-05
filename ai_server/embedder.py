import os
from threading import Lock

import cv2
import numpy as np
import onnxruntime as ort
from insightface.app import FaceAnalysis

from ai_server import utils


_app: FaceAnalysis | None = None
_app_lock = Lock()
DEFAULT_ONNX_THREADS = 1


def _get_onnx_session_options() -> ort.SessionOptions:
    """Set thread counts explicitly so ONNX Runtime does not set CPU affinity."""
    try:
        num_threads = int(os.getenv("ONNXRUNTIME_NUM_THREADS", DEFAULT_ONNX_THREADS))
    except ValueError:
        num_threads = DEFAULT_ONNX_THREADS

    session_options = ort.SessionOptions()
    session_options.intra_op_num_threads = num_threads
    session_options.inter_op_num_threads = num_threads
    return session_options


def get_face_app() -> FaceAnalysis:
    """Load InsightFace lazily so the API can start before model download."""
    global _app
    if _app is not None:
        return _app

    with _app_lock:
        if _app is None:
            print("Dang tai model Buffalo_L. Vui long cho...")
            app = FaceAnalysis(
                name="buffalo_l",
                providers=["CPUExecutionProvider"],
                sess_options=_get_onnx_session_options(),
            )
            app.prepare(ctx_id=-1, det_size=(640, 640))
            _app = app
            print("Model Buffalo_L da tai xong!")
        return _app


def extract_face_data(image_bytes: bytes) -> dict | None:
    """Extract vector and quality score from the largest face in image bytes."""
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return None

        faces = get_face_app().get(img)
        if not faces:
            return None

        faces_sorted = sorted(
            faces,
            key=lambda face: (face.bbox[2] - face.bbox[0])
            * (face.bbox[3] - face.bbox[1]),
            reverse=True,
        )
        best_face = faces_sorted[0]
        embedding = best_face.normed_embedding.tolist()
        quality_score = utils.calculate_face_quality(image=img, face=best_face)

        return {
            "vector": embedding,
            "face_quality": quality_score,
            "det_score": float(best_face.det_score),
        }
    except Exception as error:
        print(f"Error extracting face vector: {error}")
        return None


def get_vector(image_bytes: bytes) -> list[float] | None:
    """Backward-compatible helper for callers that only need the face vector."""
    face_data = extract_face_data(image_bytes=image_bytes)
    if not face_data:
        return None
    return face_data["vector"]
