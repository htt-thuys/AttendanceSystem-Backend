from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index, func
from sqlalchemy.orm import relationship

from infrastructure.database.models.base import Base


class AttendanceRecord(Base):
    """Bảng attendance_records - thông tin điểm danh nhân viên."""

    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_attendance_employee_date"),
        Index("ix_attendance_date", "date"),
        Index("ix_attendance_employee_date", "employee_id", "date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    check_in_time = Column(DateTime(timezone=True), nullable=True)
    check_out_time = Column(DateTime(timezone=True), nullable=True)
    check_in_log_id = Column(Integer, ForeignKey("recognition_logs.id"), nullable=True)
    check_out_log_id = Column(Integer, ForeignKey("recognition_logs.id"), nullable=True)
    status = Column(String(20), default="absent", nullable=False)
    work_hours = Column(Float, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    employee = relationship("Employee", back_populates="attendance_records")
    check_in_log = relationship("RecognitionLog", foreign_keys=[check_in_log_id])
    check_out_log = relationship("RecognitionLog", foreign_keys=[check_out_log_id])
