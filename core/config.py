from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "face_embeddings"

    # Storage
    IMAGE_STORAGE_PATH: str = "./storage/images"
    RECOGNITION_LOGS_DIR: str = "recognition_logs"
    VECTOR_SOURCES_DIR: str = "vector_sources"
    UNKNOWN_QUEUE_DIR: str = "unknown_queue"
    AVATARS_DIR: str = "avatars"
    IMAGE_RETENTION_DAYS: int = 7
    IMAGE_CLEANUP_INTERVAL_HOURS: int = 24
    ADMIN_VECTOR_UPLOAD_LIMIT: int = 5
    IMAGE_PUBLIC_BASE: str = "/media"
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    BACKEND_CORS_ORIGIN_REGEX: str = ""

    # Email / SMTP
    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_FROM_NAME: str = "Attendance System"
    SMTP_USE_TLS: bool = True
    SMTP_TIMEOUT_SECONDS: int = 10

    # Auth
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1

    # AI server
    AI_SERVER_HOST: str = "172.16.75.66"
    AI_SERVER_EMBED_PORT: int = 8002
    AI_SERVER_PREFIX: str = "/api/v1"
    AI_SERVER_TIMEOUT: int = 10

    # Thresholds (Buffalo_L cosine similarity)
    SURE_THRESHOLD: float = 0.40     # similarity >= này + gap >= GAP_MIN → SURE
    REVIEW_LOW: float = 0.25         # similarity trong khoảng này hoặc gap GAP_MIN <→ REVIEW
    GAP_MIN: float = 0.08            # gap giữa top-1 và top-2 employee

    # Selective upsert
    UPSERT_SCORE_MAX: float = 0.50   # score < này → upsert (ảnh góc mới, có ích)
    UPSERT_MIN_VECS: int = 5         # hoặc người có ít hơn N vector → luôn upsert

    # Dedup unknown_queue
    DEDUP_THRESHOLD: float = 0.30    # similarity > này → cùng người, cập nhật bản ghi

    RECOGNITION_LOG_COOLDOWN_MINUTES: int = 15
    EVENT_TABLET_LOOKAHEAD_MINUTES: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def cors_origin_regex(self) -> str | None:
        value = self.BACKEND_CORS_ORIGIN_REGEX.strip()
        return value or None


settings = Settings()
