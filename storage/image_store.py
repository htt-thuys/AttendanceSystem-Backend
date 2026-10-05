import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from core.config import settings


def ensure_storage_dirs() -> None:
    """Tạo sẵn các thư mục gốc để lưu ảnh nếu chúng chưa tồn tại."""
    root = Path(settings.IMAGE_STORAGE_PATH)
    root.mkdir(parents=True, exist_ok=True)
    (root / settings.RECOGNITION_LOGS_DIR).mkdir(parents=True, exist_ok=True)
    (root / settings.VECTOR_SOURCES_DIR).mkdir(parents=True, exist_ok=True)
    (root / settings.UNKNOWN_QUEUE_DIR).mkdir(parents=True, exist_ok=True)
    (root / settings.AVATARS_DIR).mkdir(parents=True, exist_ok=True)


def normalize_relative_path(relative_path: str) -> str:
    """Chuẩn hóa đường dẫn tương đối để lưu trong database và trả về cho API."""
    return Path(relative_path).as_posix()


def get_absolute_image_path(relative_path: str) -> Path:
    """Đổi đường dẫn tương đối trong database thành đường dẫn tuyệt đối trên đĩa."""
    return Path(settings.IMAGE_STORAGE_PATH) / Path(relative_path)


def build_image_url(relative_path: str | None) -> str | None:
    """Tạo URL public để Frontend có thể hiển thị ảnh từ đường dẫn tương đối."""
    if not relative_path:
        return None
    clean_path = normalize_relative_path(relative_path).lstrip("/")
    return f"{settings.IMAGE_PUBLIC_BASE.rstrip('/')}/{clean_path}"


def _build_file_name(extension: str, captured_at: datetime | None = None) -> str:
    captured_at = captured_at or datetime.now()
    stamp = captured_at.strftime("%Y%m%d_%H%M%S_%f")
    return f"{stamp}_{uuid.uuid4().hex[:8]}{extension}"


def _normalize_extension(original_name: str | None = None) -> str:
    if original_name:
        suffix = Path(original_name).suffix.lower()
        if suffix:
            return suffix
    return ".jpg"


def _build_dated_relative_path(category: str, extension: str, captured_at: datetime | None = None) -> str:
    captured_at = captured_at or datetime.now()
    day_folder = captured_at.strftime("%Y-%m-%d")
    file_name = _build_file_name(extension=extension, captured_at=captured_at)
    return normalize_relative_path(Path(category) / day_folder / file_name)


def _get_day_folder_from_source(source_relative_path: str) -> str:
    parts = Path(source_relative_path).parts
    if len(parts) >= 3 and len(parts[1]) == 10:
        return parts[1]
    return datetime.now().strftime("%Y-%m-%d")


def _write_bytes(relative_path: str, image_bytes: bytes) -> None:
    destination = get_absolute_image_path(relative_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "wb") as file_obj:
        file_obj.write(image_bytes)


def _copy_file(source_relative_path: str, destination_relative_path: str) -> str:
    source = get_absolute_image_path(source_relative_path)
    destination = get_absolute_image_path(destination_relative_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return normalize_relative_path(destination_relative_path)


async def save_recognition_log_image(image_bytes: bytes, original_name: str | None = None) -> str:
    """Lưu ảnh gốc của lần nhận diện vào thư mục recognition_logs theo ngày."""
    ensure_storage_dirs()
    relative_path = _build_dated_relative_path(
        category=settings.RECOGNITION_LOGS_DIR,
        extension=_normalize_extension(original_name),
    )
    _write_bytes(relative_path=relative_path, image_bytes=image_bytes)
    return relative_path


async def save_vector_source_image(image_bytes: bytes, original_name: str | None = None) -> str:
    """Lưu ảnh upload trực tiếp để tạo vector mới vào thư mục vector_sources theo ngày."""
    ensure_storage_dirs()
    relative_path = _build_dated_relative_path(
        category=settings.VECTOR_SOURCES_DIR,
        extension=_normalize_extension(original_name),
    )
    _write_bytes(relative_path=relative_path, image_bytes=image_bytes)
    return relative_path


async def save_avatar_image(image_bytes: bytes, employee_id: int, original_name: str | None = None) -> str:
    """Lưu ảnh đại diện của nhân viên vào thư mục avatars riêng theo nhân viên."""
    ensure_storage_dirs()
    relative_path = normalize_relative_path(
        Path(settings.AVATARS_DIR)
        / str(employee_id)
        / _build_file_name(extension=_normalize_extension(original_name))
    )
    _write_bytes(relative_path=relative_path, image_bytes=image_bytes)
    return relative_path


async def copy_to_vector_source(source_relative_path: str) -> str:
    """Sao chép ảnh đã có sang thư mục vector_sources để gắn đúng với một vector cụ thể."""
    ensure_storage_dirs()
    source_path = Path(source_relative_path)
    destination_relative_path = normalize_relative_path(
        Path(settings.VECTOR_SOURCES_DIR)
        / _get_day_folder_from_source(source_relative_path)
        / source_path.name
    )
    return _copy_file(source_relative_path=source_relative_path, destination_relative_path=destination_relative_path)


async def copy_to_unknown_queue(source_relative_path: str) -> str:
    """Sao chép ảnh đã có sang thư mục unknown_queue để làm ảnh đại diện của hàng đợi."""
    ensure_storage_dirs()
    source_path = Path(source_relative_path)
    destination_relative_path = normalize_relative_path(
        Path(settings.UNKNOWN_QUEUE_DIR)
        / _get_day_folder_from_source(source_relative_path)
        / source_path.name
    )
    return _copy_file(source_relative_path=source_relative_path, destination_relative_path=destination_relative_path)


async def copy_to_avatar(source_relative_path: str, employee_id: int) -> str:
    """Sao chép ảnh đã có sang thư mục avatars để dùng làm ảnh đại diện nhân viên."""
    ensure_storage_dirs()
    source_path = Path(source_relative_path)
    destination_relative_path = normalize_relative_path(
        Path(settings.AVATARS_DIR) / str(employee_id) / source_path.name
    )
    return _copy_file(source_relative_path=source_relative_path, destination_relative_path=destination_relative_path)


async def delete_image(relative_path: str | None) -> None:
    """Xóa file ảnh trên đĩa nếu nó còn tồn tại."""
    if not relative_path:
        return
    absolute_path = get_absolute_image_path(relative_path)
    if absolute_path.exists():
        try:
            os.remove(absolute_path)
        except OSError as error:
            print(f"Lỗi khi xóa file ảnh {absolute_path}: {error}")
