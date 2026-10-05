ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin123"
EMPLOYEE_PASSWORD = "employee123"

EMPLOYEES = [
    {
        "full_name": "Nguyen Van An",
        "employee_code": "EMP001",
        "username": "an",
        "email": "an@example.com",
        "avatar_path": "avatars/test/emp001.jpg",
    },
    {
        "full_name": "Tran Thi Binh",
        "employee_code": "EMP002",
        "username": "binh",
        "email": "binh@example.com",
        "avatar_path": "avatars/test/emp002.jpg",
    },
    {
        "full_name": "Le Minh Chau",
        "employee_code": "EMP003",
        "username": "chau",
        "email": "chau@example.com",
        "avatar_path": "avatars/test/emp003.jpg",
    },
]

CAMERA_LOCATION = "Main Entrance"

UNKNOWN_QUEUE_SEED = {
    "image_path": "unknown_queue/test/unknown_seed_001.jpg",
    "vector": [0.01] * 512,
    "face_quality": 228.5,
    "attempt_count": 2,
}


def build_seed_vector(index: int) -> list[float]:
    vector = [0.0] * 512
    vector[index - 1] = 1.0
    vector[128 + index] = 0.05 * index
    vector[256 + index] = 0.01 * index
    return vector
