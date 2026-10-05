"""
main.py - FastAPI entry point.
"""

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import settings
from infrastructure.cleanup import cleanup_old_images, run_periodic_cleanup
from infrastructure.startup_checks import run_startup_checks
from storage.image_store import ensure_storage_dirs

ensure_storage_dirs()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi động server, tạo collection Qdrant và bật job cleanup ảnh định kỳ."""
    ensure_storage_dirs()
    await run_startup_checks()
    print("Khởi động: đang chạy cleanup ảnh lần đầu...")
    await cleanup_old_images()
    print("Khởi động: cleanup ảnh lần đầu hoàn tất")
    cleanup_task = asyncio.create_task(run_periodic_cleanup())
    print("Server da khoi dong")
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
        print("Server dang tat")


app = FastAPI(
    title="Face Recognition Attendance System",
    description="He thong diem danh nhan dien khuon mat dung Buffalo_L + Qdrant + PostgreSQL",
    version="0.1.0",
    lifespan=lifespan,
)

cors_origins = settings.cors_origins
allow_origin_regex = ".*" if "*" in cors_origins else None
if allow_origin_regex:
    cors_origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    settings.IMAGE_PUBLIC_BASE,
    StaticFiles(directory=settings.IMAGE_STORAGE_PATH),
    name="media",
)


@app.get("/health", tags=["System"])
async def health_check():
    """Kiem tra server co dang chay khong."""
    return {"status": "ok"}


from api.router import router as api_router

app.include_router(api_router, prefix="/api")
