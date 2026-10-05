import cv2
import numpy as np


def calculate_blur_score(image: np.ndarray) -> float:
    """Tính độ nét của ảnh bằng phương sai Laplacian, điểm càng cao ảnh càng rõ."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    score = cv2.Laplacian(gray, cv2.CV_64F).var()
    return float(score)


def check_face_quality(face, min_det_score: float = 0.6) -> bool:
    """Kiểm tra nhanh khuôn mặt có đạt ngưỡng detection score tối thiểu hay không."""
    return bool(face.det_score >= min_det_score)


def get_face_crop(image: np.ndarray, face) -> np.ndarray:
    """Cắt vùng khuôn mặt lớn nhất từ ảnh gốc để phục vụ tính điểm chất lượng."""
    x1, y1, x2, y2 = [int(value) for value in face.bbox]
    height, width = image.shape[:2]
    x1 = max(0, min(x1, width))
    x2 = max(0, min(x2, width))
    y1 = max(0, min(y1, height))
    y2 = max(0, min(y2, height))
    if x2 <= x1 or y2 <= y1:
        return image
    return image[y1:y2, x1:x2]


def calculate_face_quality(image: np.ndarray, face) -> float:
    """Tính điểm chất lượng ảnh khuôn mặt dựa trên độ nét và detection score."""
    face_crop = get_face_crop(image=image, face=face)
    blur_score = calculate_blur_score(face_crop)
    return float(blur_score * max(float(face.det_score), 0.0))
