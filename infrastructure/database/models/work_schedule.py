from sqlalchemy import Boolean, Column, DateTime, Integer, String, Time, func

from infrastructure.database.models.base import Base


class WorkSchedule(Base):
    """Bảng work_schedules - cấu hình lịch làm việc."""

    __tablename__ = "work_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    late_threshold_minutes = Column(Integer, default=15, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
