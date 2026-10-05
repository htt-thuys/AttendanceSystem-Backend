from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from infrastructure.database.models.base import Base


class Employee(Base):
    """Bang employees - thong tin nhan vien."""

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(Text, nullable=False)
    employee_code = Column(String(50), unique=True, nullable=False)
    avatar_path = Column(Text, nullable=True)
    status = Column(String(20), default="active", nullable=False)
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(
        Integer,
        ForeignKey("users.id", use_alter=True, name="fk_employee_created_by"),
        nullable=True,
    )

    face_vectors = relationship("FaceVector", back_populates="employee")
    recognition_logs = relationship("RecognitionLog", back_populates="employee")
    meeting_participants = relationship("MeetingParticipant", back_populates="employee")
    attendance_records = relationship("AttendanceRecord", back_populates="employee")
    user_account = relationship(
        "User",
        foreign_keys="[User.employee_id]",
        back_populates="employee",
        uselist=False,
    )
    creator = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_employees",
    )
