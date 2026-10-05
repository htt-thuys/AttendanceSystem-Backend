from core.config import settings
from infrastructure.database.session import check_postgres_connection
from infrastructure.vector_db.qdrant_client import check_qdrant_connection, ensure_collection_exists


async def run_startup_checks() -> None:
    await _check_postgres_or_raise()
    _check_qdrant_or_raise()
    _ensure_qdrant_collection_or_raise()


async def _check_postgres_or_raise() -> None:
    print("Khoi dong: dang kiem tra PostgreSQL...")
    try:
        await check_postgres_connection()
    except Exception as error:
        raise RuntimeError(
            "Loi khoi dong: Khong ket noi duoc PostgreSQL. "
            "Hay kiem tra PostgreSQL da bat chua va DATABASE_URL trong .env co dung khong."
        ) from error
    print("Khoi dong: PostgreSQL OK")


def _check_qdrant_or_raise() -> None:
    print("Khoi dong: dang kiem tra Qdrant...")
    try:
        check_qdrant_connection()
    except Exception as error:
        raise RuntimeError(
            f"Loi khoi dong: Khong ket noi duoc Qdrant tai {settings.QDRANT_URL}. "
            "Hay kiem tra Qdrant da bat chua va QDRANT_URL trong .env co dung khong."
        ) from error
    print("Khoi dong: Qdrant OK")


def _ensure_qdrant_collection_or_raise() -> None:
    print(f"Khoi dong: dang kiem tra collection '{settings.QDRANT_COLLECTION}'...")
    try:
        ensure_collection_exists()
    except Exception as error:
        raise RuntimeError(
            f"Loi khoi dong: Khong the kiem tra hoac tao collection '{settings.QDRANT_COLLECTION}' tren Qdrant."
        ) from error
    print(f"Khoi dong: collection '{settings.QDRANT_COLLECTION}' OK")
