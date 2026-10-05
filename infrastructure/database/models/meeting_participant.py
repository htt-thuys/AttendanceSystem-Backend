from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from infrastructure.database.models.base import Base


class MeetingParticipant(Base):
    """Bang meeting_participants - danh sach nguoi tham gia cuoc hop."""

    __tablename__ = "meeting_participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    status = Column(String(20), default="invited", nullable=False)
    check_in_time = Column(DateTime(timezone=True), nullable=True)
    check_in_log_id = Column(Integer, ForeignKey("recognition_logs.id"), nullable=True)
    check_out_time = Column(DateTime(timezone=True), nullable=True)
    check_out_log_id = Column(Integer, ForeignKey("recognition_logs.id"), nullable=True)
    note = Column(Text, nullable=True)

    meeting = relationship("Meeting", back_populates="participants")
    employee = relationship("Employee", back_populates="meeting_participants")
    check_in_log = relationship("RecognitionLog", foreign_keys=[check_in_log_id])
    check_out_log = relationship("RecognitionLog", foreign_keys=[check_out_log_id])
